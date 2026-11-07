import json,tempfile,shutil,unittest
from pathlib import Path
from unittest.mock import patch
import services.incremental_service as inc

class IncrementalTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.assets=self.root/'assets';self.config=self.root/'config';self.game=self.root/'game.pak';self.game.write_bytes(b'game')
  self.base='HerovsGame/Content/Character/Ch001/PA_Ch001'
  self.source={self.base+'.uasset':b'asset',self.base+'.uexp':b'first'}
  self.calls=[];self.fail=False
  self.patches=[patch.object(inc,'ASSETS_DIR',str(self.assets)),patch.object(inc,'CONFIG_DIR',str(self.config)),patch.object(inc,'run_hidden_command',self.command),patch('services.cache_service.update_startup_cache')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def command(self,args,*a,**kw):
  self.calls.append(args)
  if 'list' in args:return {'stdout':'\n'.join(self.source)}
  if 'unpack' in args:
   folder=Path(args[args.index('-o')+1])
   for name,content in self.source.items():
    p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
   return {'stdout':''}
  if '-e' in args:
   if self.fail:raise RuntimeError('conversion failed')
   path=Path(args[-1]);path.with_suffix('.json').write_text(json.dumps({'data':path.with_suffix('.uexp').read_text()}))
   return {'stdout':''}
  raise AssertionError(args)
 def refresh(self):return inc.refresh_assets('key',str(self.game))
 def test_second_pass_never_opens_pak_or_converter(self):
  self.assertEqual(self.refresh()['converted'],1);self.calls.clear()
  result=self.refresh();self.assertTrue(result['used_cache']);self.assertEqual(self.calls,[])
 def test_companion_change_reconverts(self):
  self.refresh();self.source[self.base+'.uexp']=b'changed';self.game.write_bytes(b'new game')
  result=self.refresh();self.assertEqual(result['updated_files'],1);self.assertEqual(result['converted'],1)
  self.assertEqual(json.loads((self.assets/(self.base+'.json')).read_text())['data'],'changed')
 def test_corrupt_output_repaired_without_extraction(self):
  self.refresh();(self.assets/(self.base+'.json')).write_text('corrupt');self.calls.clear()
  self.assertEqual(self.refresh()['converted'],1)
  self.assertFalse(any('unpack' in args or 'list' in args for args in self.calls))
 def test_failed_conversion_is_retried_and_old_output_preserved(self):
  self.refresh();self.source[self.base+'.uexp']=b'changed';self.game.write_bytes(b'new game');self.fail=True
  result=self.refresh();self.assertTrue(result['warnings'])
  self.assertEqual(json.loads((self.assets/(self.base+'.json')).read_text())['data'],'first')
  self.fail=False;self.assertEqual(self.refresh()['converted'],1)
 def test_filter_excludes_unrelated_assets(self):
  self.assertTrue(inc.catalog_entry('HerovsGame/Content/Character/Ch001/GUI/Costume/L/T_ui_Thumb_4_1000000_L.uasset'))
  self.assertFalse(inc.catalog_entry('HerovsGame/Content/Character/Ch001/GUI/Costume/L/T_ui_Thumb_4_1000000_L_Sprite.uasset'))
