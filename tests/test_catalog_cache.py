import io,json,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
from services import catalog_web_service as web

class Response(io.BytesIO):
 headers={'ETag':'"v1"'}
class CatalogCacheTests(unittest.TestCase):
 def test_http_304_reuses_verified_html(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(web,'CONFIG_DIR',temp):
   with patch.object(web.urllib.request,'urlopen',return_value=Response(b'<html>cached</html>')):self.assertEqual(web.fetch_text('https://ultrarumble.com/costumes'),'<html>cached</html>')
   def conditional(request,**kwargs):
    self.assertEqual(request.get_header('If-none-match'),'"v1"')
    raise urllib.error.HTTPError(request.full_url,304,'Not modified',{},None)
   with patch.object(web.urllib.request,'urlopen',side_effect=conditional):self.assertEqual(web.fetch_text('https://ultrarumble.com/costumes'),'<html>cached</html>')
 def test_unchanged_entries_do_not_rewrite_catalog(self):
  from services.catalog_service import upsert_catalog_entry
  catalog=upsert_catalog_entry({'_meta':{}},'Ch001','1','SK_Test',display_name='Test',display_name_es='Prueba',description='Description',description_es='Texto',source_url='https://ultrarumble.com/costume/1')
  entries=[dict(character_code='Ch001',skin_id='1',display_name='Test',description='Description',source_url='url')]
  with patch.object(web,'load_catalog',return_value=catalog),patch.object(web,'fetch_web_catalog',return_value=entries),patch.object(web,'save_catalog') as save:
   result=web.merge_web_catalog_into_local('en',{'Ch001':{'1':'SK_Test'}})
   self.assertEqual(result['changed_count'],0);save.assert_not_called()

 def test_current_catalog_markup_and_reordered_attributes(self):
  html='<a title="Hero &amp; Costume" class="co-tile" href="/costume/1000000"><img loading="lazy" src="/assets/Character/Ch001/GUI/Costume/S/image.png"><small>Hero</small></a>'
  entries=web.extract_costume_entries_from_list(html,'https://ultrarumble.com')
  self.assertEqual(len(entries),1)
  self.assertEqual(entries[0]['display_name'],'Hero & Costume')
  self.assertEqual(entries[0]['character_code'],'Ch001')

 def test_old_catalog_markup_still_supported(self):
  html='<a href="/costume/1000000"><img title="Description" src="/assets/Character/Ch001/GUI/Costume/L/image.png"><div class="name">Hero</div></a>'
  entries=web.extract_costume_entries_from_list(html,'https://ultrarumble.com')
  self.assertEqual(entries[0]['display_name'],'Hero')
  self.assertEqual(entries[0]['description'],'Description')
