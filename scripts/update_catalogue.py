#!/usr/bin/env python3
"""Update wrestling video catalogue exclusively from configured official publishers.

Standard-library only. Runs with YouTube public channel Atom feeds without keys.
With YOUTUBE_API_KEY, uses documented YouTube Data API endpoints to enrich video
metadata, screen UK region restrictions and verify live/upcoming broadcasts.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
VIDEO_ID = re.compile(r'^[a-zA-Z0-9_-]{11}$')
UA = 'WrestleStream/0.1 (+noncommercial official-link aggregator)'


def get_url(url):
    request = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json, application/atom+xml, application/xml'})
    with urllib.request.urlopen(request, timeout=22) as resp:
        return resp.read()


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def classify(title, duration=None):
    low = title.casefold()
    if '#shorts' in low or (duration is not None and duration <= 60):
        return 'Short'
    if re.search(r'full (episode|show|event)|complete (episode|show)|entire episode|fusion \(full episode\)', low):
        return 'Full show'
    if re.search(r'full match|complete match|free match|match in full', low):
        return 'Full match'
    if re.search(r'highlight|recap|top 10|best of|moments', low):
        return 'Highlights'
    if re.search(r'documentary|behind the scenes|the story of', low):
        return 'Documentary'
    if re.search(r'interview|press conference|media scrum', low):
        return 'Interview'
    if re.search(r' vs\.? | v\. |\bmatch\b|\bfaces?\b|\btakes on\b', low):
        return 'Match / segment'
    return 'Other'


def parse_duration(raw):
    match = re.fullmatch(r'P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', raw or '')
    if not match:
        return None
    return int(match.group(1) or 0)*3600+int(match.group(2) or 0)*60+int(match.group(3) or 0)


def parse_feed(body, source):
    root = ET.fromstring(body)
    videos = []
    for entry in root.findall('a:entry', NS):
        vid = entry.findtext('yt:videoId', default='', namespaces=NS)
        title = entry.findtext('a:title', default='', namespaces=NS).strip()
        published = entry.findtext('a:published', default='', namespaces=NS)
        if not VIDEO_ID.fullmatch(vid) or not title:
            continue
        videos.append({
            'id': 'yt-'+vid, 'platform': 'youtube', 'video_id': vid,
            'title': title, 'promotion': source['name'], 'source_id': source['id'],
            'country': source['country'], 'published': published,
            'type': classify(title), 'duration_seconds': None,
            'url': f'https://www.youtube.com/watch?v={vid}', 'is_live': False,
            'embed_allowed': True
        })
    return videos


def api_call(endpoint, key, **parameters):
    parameters['key'] = key
    url = 'https://www.googleapis.com/youtube/v3/'+endpoint+'?'+urllib.parse.urlencode(parameters)
    return json.loads(get_url(url))


def gb_accessible(video):
    details = video.get('contentDetails') or {}
    geo = details.get('regionRestriction') or {}
    if 'blocked' in geo and 'GB' in geo['blocked']:
        return False
    if 'allowed' in geo and 'GB' not in geo['allowed']:
        return False
    return True


def fetch_details(ids, api_key):
    output = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        payload = api_call('videos', api_key, part='snippet,contentDetails,status,liveStreamingDetails', id=','.join(chunk), maxResults=50)
        output.update({v['id']: v for v in payload.get('items', [])})
    return output


def from_api(source, api_key):
    channel_id = source['channel_id']
    channel_info = api_call('channels', api_key, part='contentDetails', id=channel_id)
    items = channel_info.get('items') or []
    if not items:
        raise RuntimeError('Channel ID not found')
    uploads = items[0]['contentDetails']['relatedPlaylists']['uploads']
    playlist = api_call('playlistItems', api_key, part='snippet,contentDetails', playlistId=uploads, maxResults=35)
    ids = [entry.get('contentDetails', {}).get('videoId') for entry in playlist.get('items', [])]
    ids = [v for v in ids if v and VIDEO_ID.fullmatch(v)]
    details = fetch_details(ids, api_key)
    result = []
    for vid in ids:
        video = details.get(vid)
        if not video or not gb_accessible(video):
            continue
        s = video.get('snippet') or {}
        status = video.get('status') or {}
        if status.get('privacyStatus') != 'public':
            continue
        if s.get('channelId') != channel_id:
            continue
        if s.get('liveBroadcastContent') == 'upcoming':
            continue  # These are shown in the TV guide, not mislabelled as VOD.
        duration = parse_duration((video.get('contentDetails') or {}).get('duration'))
        title = s.get('title', '').strip()
        if not title:
            continue
        result.append({
            'id': 'yt-'+vid, 'platform': 'youtube', 'video_id': vid,
            'title': title, 'promotion': source['name'], 'source_id': source['id'],
            'country': source['country'], 'published': s.get('publishedAt'),
            'type': classify(title, duration), 'duration_seconds': duration,
            'url': f'https://www.youtube.com/watch?v={vid}',
            'is_live': s.get('liveBroadcastContent') == 'live',
            'embed_allowed': status.get('embeddable', True)
        })
    return result


def from_api_live(source, api_key):
    ids = []
    # Searching a specific trusted channel, never arbitrary uploader accounts.
    for event_type in ('live', 'upcoming'):
        result = api_call('search', api_key, part='snippet', channelId=source['channel_id'],
                          eventType=event_type, type='video', maxResults=10)
        for item in result.get('items', []):
            vid = (item.get('id') or {}).get('videoId')
            if vid and VIDEO_ID.fullmatch(vid) and vid not in ids:
                ids.append(vid)
    details = fetch_details(ids, api_key)
    live = []
    for vid in ids:
        video = details.get(vid)
        if not video or not gb_accessible(video):
            continue
        s = video.get('snippet') or {}
        status = video.get('status') or {}
        ls = video.get('liveStreamingDetails') or {}
        if status.get('privacyStatus') != 'public' or s.get('channelId') != source['channel_id']:
            continue
        if ls.get('actualEndTime'):
            continue
        broadcast = s.get('liveBroadcastContent')
        start = ls.get('actualStartTime') if broadcast=='live' else ls.get('scheduledStartTime')
        if broadcast not in ('live', 'upcoming') or not start:
            continue
        # Only offer verifiable *public* events on the official publisher channel.
        live.append({'id':'yt-'+vid,'title':s.get('title','Official live wrestling'),
                     'promotion':source['name'],'source_id':source['id'],
                     'country':source['country'],'start_time':start,
                     'status':broadcast,'url':f'https://www.youtube.com/watch?v={vid}'})
    return live


def refresh(existing, sources, key=None):
    existing_videos = existing.get('videos', [])
    by_id = {v['id']: v for v in existing_videos if isinstance(v, dict) and v.get('id')}
    old_live = existing.get('live') or []
    fresh_live = []
    success = 0
    for source in sources:
        if not source.get('auto') or not source.get('channel_id'):
            continue
        try:
            if key:
                videos = from_api(source, key)
                live = from_api_live(source, key)
                fresh_live.extend(live)
            else:
                url = 'https://www.youtube.com/feeds/videos.xml?channel_id='+source['channel_id']
                videos = parse_feed(get_url(url), source)
            if not videos and not key:
                raise RuntimeError('Feed had no usable entries')
            success += 1
            for v in videos:
                old = by_id.get(v['id'])
                if old and old.get('embed_allowed') is False and 'embed_allowed' not in v:
                    v['embed_allowed'] = False
                by_id[v['id']] = v
            print(f"OK {source['name']}: {len(videos)} uploads")
        except (Exception) as exc:
            # Never overwrite source catalogue with invented or empty results.
            print(f"WARNING {source['name']}: {exc}", file=sys.stderr)
    if success == 0:
        raise RuntimeError('No source succeeded. Existing catalogue left untouched.')
    by_id = {k: v for k, v in by_id.items() if v.get('platform') in ('youtube','external')}
    all_videos = sorted(by_id.values(), key=lambda v: v.get('published') or '', reverse=True)
    # Keyless RSS provides no trusted real-time schedule. Preserve no stale LIVE claims.
    # API mode is the only mode that produces current verified live guide data.
    return {'generated_at': now_iso(), 'mode': 'youtube-api' if key else 'public-rss',
            'notice': 'YouTube official-source updates. UK restrictions checked only in API mode.',
            'videos': all_videos[:450], 'live': fresh_live if key else []}


def main():
    sources = json.loads((ROOT/'data/sources.json').read_text(encoding='utf-8'))
    file = ROOT/'data/catalogue.json'
    existing = json.loads(file.read_text(encoding='utf-8'))
    latest = refresh(existing, sources, os.environ.get('YOUTUBE_API_KEY'))
    draft = file.with_suffix('.json.tmp')
    draft.write_text(json.dumps(latest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    draft.replace(file)
    print(f"Wrote {len(latest['videos'])} videos and {len(latest['live'])} verified live broadcasts.")

if __name__=='__main__':
    main()
