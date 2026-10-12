import unittest
from unittest.mock import patch
from scripts.update_catalogue import classify, parse_feed, parse_duration, gb_accessible, refresh
S = {'id':'mlw','name':'MLW','country':'USA','channel_id':'UCNL6Rxxy-LtEdwH3YPbVS2g','auto':True}
FEED = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><entry><yt:videoId>E0PvsiNpoz4</yt:videoId><title>MLW Fusion (Full Episode)</title><published>2026-07-11T12:00:00+00:00</published></entry></feed>'''
class TestCatalogue(unittest.TestCase):
    def test_title_classification(self):
        self.assertEqual(classify('MLW Fusion: Full Episode'),'Full show')
        self.assertEqual(classify('New Free Match Released'),'Full match')
        self.assertEqual(classify('Weekend highlights'),'Highlights')
        self.assertEqual(classify('A new press conference'),'Interview')
        self.assertEqual(classify('Random title'),'Other')
    def test_duration(self):
        self.assertEqual(parse_duration('PT1H02M03S'),3723)
        self.assertEqual(parse_duration('PT59S'),59)
        self.assertIsNone(parse_duration('garbage'))
    def test_rss(self):
        videos=parse_feed(FEED,S)
        self.assertEqual(len(videos),1)
        self.assertEqual(videos[0]['id'],'yt-E0PvsiNpoz4')
        self.assertEqual(videos[0]['type'],'Full show')
        self.assertFalse(videos[0]['is_live'])
    def test_uk_restriction(self):
        self.assertFalse(gb_accessible({'contentDetails':{'regionRestriction':{'blocked':['GB']}}}))
        self.assertFalse(gb_accessible({'contentDetails':{'regionRestriction':{'allowed':['US']}}}))
        self.assertTrue(gb_accessible({'contentDetails':{'regionRestriction':{'allowed':['GB']}}}))
    @patch('scripts.update_catalogue.get_url',return_value=FEED)
    def test_refresh_persists_unique_and_resets_unverified_live(self,request):
        old={'videos':[{'id':'yt-E0PvsiNpoz4','platform':'youtube','published':'2020-01-01'}],
             'live':[{'id':'fake','status':'live'}]}
        out=refresh(old,[S])
        self.assertEqual(len(out['videos']),1)
        self.assertEqual(out['live'],[])
        self.assertEqual(out['mode'],'public-rss')
    @patch('scripts.update_catalogue.get_url',side_effect=RuntimeError('Unavailable'))
    def test_failure_does_not_replace_file(self,request):
        with self.assertRaises(RuntimeError):refresh({'videos':[]},[S])
if __name__=='__main__':unittest.main()
