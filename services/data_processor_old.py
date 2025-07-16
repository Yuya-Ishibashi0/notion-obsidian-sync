"""
データ変換プロセッサー
NotionデータをMarkdown形式に変換するためのプロセッサー
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.notion import (
    NotionPage, NotionPageContent, NotionBlock, NotionProperty, 
    NotionRichText, NotionBlockType
)
from models.markdown import MarkdownFile, MarkdownConversionResult
from models.config import ConversionConfig
from services.advanced_block_converter import AdvancedBlockConverter


class DataProcessor:
    """データ変換プロセッサー"""
    
    def __init__(self, conversion_config: ConversionConfig):
        """
        初期化
        
        Args:
            conversion_config: 変換設定
        """
        self.config = conversion_config
        self.logger = logging.getLogger(__name__)
        self.block_converter = AdvancedBlockConverter(conversion_config)
    
    def extract_properties(self, page: NotionPage) -> Dict[str, Any]:
        """
        Notionページからプロパティを抽出
        
        Args:
            page: NotionPageオブジェクト
            
        Returns:
            プロパティの辞書
        """
        properties = {}
        
        try:
            for prop_name, prop in page.properties.items():
                extracted_value = self._extract_single_property(prop)
                if extracted_value is not None:
                    properties[prop_name] = extracted_value
            
            self.logger.debug(f"プロパティ抽出完了: {len(properties)}個")
            return properties
            
        except Exception as e:
            self.logger.error(f"プロパティ抽出エラー: {str(e)}")
            return {}
    
    def _extract_single_property(self, prop: NotionProperty) -> Any:
        """
        単一プロパティの値を抽出
        
        Args:
            prop: NotionPropertyオブジェクト
            
        Returns:
            抽出された値
        """
        try:
            if prop.type == "title":
                return self._extract_title_property(prop.value)
            elif prop.type == "rich_text":
                return self._extract_rich_text_property(prop.value)
            elif prop.type == "select":
                return self._extract_select_property(prop.value)
            elif prop.type == "multi_select":
                return self._extract_multi_select_property(prop.value)
            elif prop.type == "date":
                return self._extract_date_property(prop.value)
            elif prop.type == "people":
                return self._extract_people_property(prop.value)
            elif prop.type == "files":
                return self._extract_files_property(prop.value)
            elif prop.type == "checkbox":
                return self._extract_checkbox_property(prop.value)
            elif prop.type == "url":
                return self._extract_url_property(prop.value)
            elif prop.type == "email":
                return self._extract_email_property(prop.value)
            elif prop.type == "phone_number":
                return self._extract_phone_property(prop.value)
            elif prop.type == "number":
                return self._extract_number_property(prop.value)
            elif prop.type == "formula":
                return self._extract_formula_property(prop.value)
            elif prop.type == "relation":
                return self._extract_relation_property(prop.value)
            elif prop.type == "rollup":
                return self._extract_rollup_property(prop.value)
            elif prop.type in ["created_time", "last_edited_time"]:
                return self._extract_timestamp_property(prop.value)
            elif prop.type in ["created_by", "last_edited_by"]:
                return self._extract_user_property(prop.value)
            elif prop.type == "status":
                return self._extract_status_property(prop.value)
            else:
                self.logger.warning(f"未対応のプロパティタイプ: {prop.type}")
                return str(prop.value) if prop.value is not None else None
                
        except Exception as e:
            self.logger.error(f"プロパティ抽出エラー ({prop.type}): {str(e)}")
            return None
    
    def _extract_title_property(self, value: List[Dict[str, Any]]) -> str:
        """タイトルプロパティの抽出"""
        if not value:
            return ""
        return "".join([item.get("plain_text", "") for item in value])
    
    def _extract_rich_text_property(self, value: List[Dict[str, Any]]) -> str:
        """リッチテキストプロパティの抽出"""
        if not value:
            return ""
        return "".join([item.get("plain_text", "") for item in value])
    
    def _extract_select_property(self, value: Optional[Dict[str, Any]]) -> Optional[str]:
        """選択プロパティの抽出"""
        if not value:
            return None
        return value.get("name")
    
    def _extract_multi_select_property(self, value: List[Dict[str, Any]]) -> List[str]:
        """複数選択プロパティの抽出"""
        if not value:
            return []
        return [item.get("name", "") for item in value if item.get("name")]
    
    def _extract_date_property(self, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """日付プロパティの抽出"""
        if not value:
            return None
        
        result = {}
        if value.get("start"):
            result["start"] = value["start"]
        if value.get("end"):
            result["end"] = value["end"]
        if value.get("time_zone"):
            result["time_zone"] = value["time_zone"]
        
        return result if result else None
    
    def _extract_people_property(self, value: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """人物プロパティの抽出"""
        if not value:
            return []
        
        people = []
        for person in value:
            person_info = {"id": person.get("id", "")}
            if person.get("name"):
                person_info["name"] = person["name"]
            if person.get("avatar_url"):
                person_info["avatar_url"] = person["avatar_url"]
            people.append(person_info)
        
        return people
    
    def _extract_files_property(self, value: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """ファイルプロパティの抽出"""
        if not value:
            return []
        
        files = []
        for file_info in value:
            file_data = {"name": file_info.get("name", "")}
            
            if file_info.get("type") == "external":
                file_data["url"] = file_info.get("external", {}).get("url", "")
                file_data["type"] = "external"
            elif file_info.get("type") == "file":
                file_data["url"] = file_info.get("file", {}).get("url", "")
                file_data["type"] = "file"
                file_data["expiry_time"] = file_info.get("file", {}).get("expiry_time", "")
            
            files.append(file_data)
        
        return files
    
    def _extract_checkbox_property(self, value: bool) -> bool:
        """チェックボックスプロパティの抽出"""
        return bool(value)
    
    def _extract_url_property(self, value: Optional[str]) -> Optional[str]:
        """URLプロパティの抽出"""
        return value if value else None
    
    def _extract_email_property(self, value: Optional[str]) -> Optional[str]:
        """メールプロパティの抽出"""
        return value if value else None
    
    def _extract_phone_property(self, value: Optional[str]) -> Optional[str]:
        """電話番号プロパティの抽出"""
        return value if value else None
    
    def _extract_number_property(self, value: Optional[float]) -> Optional[float]:
        """数値プロパティの抽出"""
        return value if value is not None else None
    
    def _extract_formula_property(self, value: Dict[str, Any]) -> Any:
        """数式プロパティの抽出"""
        if not value:
            return None
        
        formula_type = value.get("type")
        if formula_type == "string":
            return value.get("string")
        elif formula_type == "number":
            return value.get("number")
        elif formula_type == "boolean":
            return value.get("boolean")
        elif formula_type == "date":
            return self._extract_date_property(value.get("date"))
        else:
            return str(value)
    
    def _extract_relation_property(self, value: List[Dict[str, Any]]) -> List[str]:
        """関連プロパティの抽出"""
        if not value:
            return []
        return [item.get("id", "") for item in value if item.get("id")]
    
    def _extract_rollup_property(self, value: Dict[str, Any]) -> Any:
        """ロールアッププロパティの抽出"""
        if not value:
            return None
        
        rollup_type = value.get("type")
        if rollup_type == "number":
            return value.get("number")
        elif rollup_type == "date":
            return self._extract_date_property(value.get("date"))
        elif rollup_type == "array":
            return value.get("array", [])
        else:
            return str(value)
    
    def _extract_timestamp_property(self, value: Optional[str]) -> Optional[str]:
        """タイムスタンププロパティの抽出"""
        return value if value else None
    
    def _extract_user_property(self, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """ユーザープロパティの抽出"""
        if not value:
            return None
        
        user_info = {"id": value.get("id", "")}
        if value.get("name"):
            user_info["name"] = value["name"]
        if value.get("avatar_url"):
            user_info["avatar_url"] = value["avatar_url"]
        
        return user_info
    
    def _extract_status_property(self, value: Optional[Dict[str, Any]]) -> Optional[str]:
        """ステータスプロパティの抽出"""
        if not value:
            return None
        return value.get("name")
    
    def create_frontmatter_dict(self, page: NotionPage, 
                               include_properties: bool = True) -> Dict[str, Any]:
        """
        YAMLフロントマター用の辞書を作成
        
        Args:
            page: NotionPageオブジェクト
            include_properties: プロパティを含めるかどうか
            
        Returns:
            フロントマター辞書
        """
        frontmatter = {
            "notion_id": page.id,
            "created_time": page.created_time.isoformat() if page.created_time else None,
            "last_edited_time": page.last_edited_time.isoformat() if page.last_edited_time else None,
            "archived": page.archived
        }
        
        # URLがある場合は追加
        if page.url:
            frontmatter["notion_url"] = page.url
        
        # プロパティを含める場合
        if include_properties:
            properties = self.extract_properties(page)
            
            # タイトルプロパティは特別扱い（通常はファイル名になるため）
            for prop_name, prop_value in properties.items():
                if prop_name.lower() not in ["title", "タイトル", "名前"]:
                    frontmatter[prop_name] = prop_value
        
        # 空の値を除去
        frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
        
        return frontmatter
    
    def validate_properties(self, properties: Dict[str, Any]) -> List[str]:
        """
        プロパティの検証
        
        Args:
            properties: プロパティ辞書
            
        Returns:
            警告メッセージのリスト
        """
        warnings = []
        
        for prop_name, prop_value in properties.items():
            # 長すぎるプロパティ名
            if len(prop_name) > 100:
                warnings.append(f"プロパティ名が長すぎます: {prop_name[:50]}...")
            
            # 複雑すぎるプロパティ値
            if isinstance(prop_value, (list, dict)):
                if isinstance(prop_value, list) and len(prop_value) > 50:
                    warnings.append(f"プロパティ '{prop_name}' の配列が大きすぎます: {len(prop_value)}要素")
                elif isinstance(prop_value, dict) and len(prop_value) > 20:
                    warnings.append(f"プロパティ '{prop_name}' のオブジェクトが複雑すぎます: {len(prop_value)}フィールド")
            
            # 文字列の長さチェック
            if isinstance(prop_value, str) and len(prop_value) > 1000:
                warnings.append(f"プロパティ '{prop_name}' の値が長すぎます: {len(prop_value)}文字")
        
        return warnings
    
    def convert_blocks_to_markdown(self, blocks: List[NotionBlock]) -> str:
        """
        NotionブロックリストをMarkdownに変換
        
        Args:
            blocks: NotionBlockオブジェクトのリスト
            
        Returns:
            変換されたMarkdown文字列
        """
        markdown_lines = []
        
        for block in blocks:
            try:
                converted_block = self._convert_single_block(block)
                if converted_block:
                    markdown_lines.append(converted_block)
            except Exception as e:
                self.logger.warning(f"ブロック変換エラー ({block.type}): {str(e)}")
                # エラーが発生した場合はプレースホルダーを挿入
                if self.config.unsupported_blocks == "placeholder":
                    markdown_lines.append(f"<!-- エラー: {block.type}ブロックの変換に失敗しました -->")
        
        return "\n".join(markdown_lines)
    
    def _convert_single_block(self, block: NotionBlock) -> Optional[str]:
        """
        単一のNotionブロックをMarkdownに変換
        
        Args:
            block: NotionBlockオブジェクト
            
        Returns:
            変換されたMarkdown文字列（変換不可の場合はNone）
        """
        block_type = block.type
        
        # 基本的なテキストブロック
        if block_type == "paragraph":
            return self._convert_paragraph_block(block)
        elif block_type in ["heading_1", "heading_2", "heading_3"]:
            return self._convert_heading_block(block)
        elif block_type == "bulleted_list_item":
            return self._convert_bulleted_list_block(block)
        elif block_type == "numbered_list_item":
            return self._convert_numbered_list_block(block)
        elif block_type == "to_do":
            return self._convert_todo_block(block)
        elif block_type == "quote":
            return self._convert_quote_block(block)
        elif block_type == "callout":
            return self._convert_callout_block(block)
        elif block_type == "divider":
            return self._convert_divider_block(block)
        
        # 高度なブロック
        elif block_type == "code":
            return self._convert_code_block(block)
        elif block_type == "image":
            return self._convert_image_block(block)
        elif block_type == "table":
            return self._convert_table_block(block)
        elif block_type == "table_row":
            return self._convert_table_row_block(block)
        elif block_type == "toggle":
            return self._convert_toggle_block(block)
        elif block_type == "equation":
            return self._convert_equation_block(block)
        elif block_type == "bookmark":
            return self._convert_bookmark_block(block)
        elif block_type == "file":
            return self._convert_file_block(block)
        elif block_type == "video":
            return self._convert_video_block(block)
        
        # サポートされていないブロック
        else:
            return self._handle_unsupported_block(block)
    
    def _convert_paragraph_block(self, block: NotionBlock) -> str:
        """段落ブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "paragraph")
        return text_content if text_content.strip() else ""
    
    def _convert_heading_block(self, block: NotionBlock) -> str:
        """見出しブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, block.type)
        if not text_content.strip():
            return ""
        
        level_map = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}
        prefix = level_map.get(block.type, "#")
        return f"{prefix} {text_content}"
    
    def _convert_bulleted_list_block(self, block: NotionBlock) -> str:
        """箇条書きリストブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "bulleted_list_item")
        return f"- {text_content}" if text_content.strip() else ""
    
    def _convert_numbered_list_block(self, block: NotionBlock) -> str:
        """番号付きリストブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "numbered_list_item")
        return f"1. {text_content}" if text_content.strip() else ""
    
    def _convert_todo_block(self, block: NotionBlock) -> str:
        """TODOブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "to_do")
        todo_data = block.content.get("to_do", {})
        checked = todo_data.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        return f"- {checkbox} {text_content}" if text_content.strip() else f"- {checkbox}"
    
    def _convert_quote_block(self, block: Ntr:
    換"""
        text_content = self._extract_rich_text_from_block(block, "quote")
        ret"
    
    def  str:
        """コー"
        callout_data = block.conte {})
        text_content = self._e]))
        icon})
        
        # アイコンの処理
        ico
        if in:
            if icon.goji":
                icon_text
            elif icon.get("type") ==ternal":
                icon_text = ""
            elif icon.get("type") == "file":
             "
            else:
                icon_
        else:
            t = "💡"
        
        # 設定に応じて変換方法を変更
        if s
            return fxt}"
        else:
            return f"{icon_text} {textt
    
    def _convert_divider_block(s
        """区"
        return "---"
    
    def _convert_code_block(selr:
        """コードブロックの変換"""
    {})
        text_content = self._extract_rich_text_from_content(code_data.get("rich_text", []))
        lan"")
        
        
        langu
            "plain text": "",
            script",
            "typ,
            "pythohon",
           
            "c": "c",
            "c++": "cpp",
            "c#": "csharp",
            "go": "go",
        ",
            "php": "php",
            "ruby": "ruby",
        ift",
            "kot,
            "scala": "scala",
            "shell": "bash",
            "bash": "bash",
            "powershell": "powershell",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "json": "json",
            "xml": "xml",
            "yaml": "yaml",
            "markdown": "markdown"
        }
        
        normalized_language = language_map.get(language.lo)
        
        rultn res     retur    
   e)}") {str("ページ変換エラー:ing(fadd_warnt.sul     re      le)
 markdown_fiile=down_fnResult(markversiorkdownCont = Maesul    r      
                   )
nt
       ontelback_c content=fal             ilename,
  =fallback_f   filename            wnFile(
 ile = Markdo  markdown_f     
              "
   (e)}した: {str発生しまの変換中にエラーがラー\n\nページ# エ f"ck_content =    fallba      id}.md"
  t.page.contenage_{por_= f"errfilename   fallback_
          基本的なファイルを作成合でもた場 エラーが発生し       #}")
     エラー: {str(e)or(f"ページ変換logger.err   self.  
       ption as e:cept Exce        ex         
sult
     return re
          e}")> {filenamtle} -nt.page.tinte {page_coページ変換完了:fo(f".logger.in       self               
arning)
  arning(wd_w   result.ad            nings:
 arperty_win prog  for warnin           ntmatter)
perties(frorote_palidas = self.vrty_warning  prope         検証警告
 # プロパティの              
         
 ock.type)d_blnsupported_block(unsupportesult.add_u          re
      _blocks:rted unsuppolock inpported_bunsu   for         )]
 upported(ock.is_sot bllocks if nge_content.bin paock ck for blocks = [bloported_bl  unsup
          あれば記録クがいブロッポートされていな   # サ      
               
_file)ile=markdownt(markdown_fulrsionResownConve= Markdt     resul    果を作成
      # 変換結          
             )
          tent
 own_conntent=markd      co
          atter,atter=frontm     frontm        e,
   name=filenam    file           ownFile(
 le = Markdwn_fikdo   mar  
       クトを作成ァイルオブジェdownフark    # M             

       ks_contentloc+ bine = title_lntent markdown_co         
   ツを作成ownコンテン 完全なMarkd          #  
            blocks)
ent._contrkdown(pageto_mart_blocks_.convet = self_conten  blocks      換
    ンテンツを変 # ブロックコ      
              \n"
   .title}\ntent.page_con"# {pagee = f_lintle ti       ル
    タイトージ       # ペ
                   )
   es
       perti_proes=includeperti_prolude        inc     
   , t.pageene_cont    pag       t(
     r_dicteontmatlf.create_frse= r tentmat        froマターを作成
         # フロント       
     )
       _patterning, file_namntent.pageage_co_filename(pgenerate= self._me      filena   生成
    ル名を   # ファイ       try:
          "
        ""ブジェクト
sultオnReConversiowndo    Mark      rns:
    Retu 
            か
     含めるかどうターにィをフロントマties: プロパテ_properde      inclu      ーン
 ファイル名のパタng_pattern: file_nami      ェクト
     ntオブジPageConteion: Not_content   page       
       Args:   
        
downファイルに変換onページをMark       Noti  """
 t:
      rsionResulownConve -> Markde) Trubool =operties: princlude_                          
      {title}", = "attern: strile_naming_p           f              
       t, onPageContenNotitent: page_conlf, own(serkdo_manvert_page_t   def corts)

 sult_pan(reoi"".j return   
          )
   _textormattedppend(fs.a_partesult         r     
          )"
xt}]({href}atted_teormt = f"[{ftted_texforma         f:
       if hre          理
  # リンクの処                
      `"
  _text}tted`{forma"ext = ftted_trma       fo
         ode"):ns.get("cotatio    if ann
        _text}</u>"ttedforma"<u>{ = fed_text    formatt       
     ため、強調で代用downには下線がないMark#         
        rline"):"undeget(ons.f annotati i           xt}~~"
teformatted_ f"~~{ted_text =     format       :
    ugh")ethrotrikions.get("sat    if annot"
        d_text}*"*{formatted_text = frmatte        fo    ic"):
    s.get("italnnotation  if a       
   text}**"atted_{formf"**d_text =   formatte         d"):
     t("bol.gensationnot       if a   
   
           lain_textted_text = pormat  f         の装飾を適用
       # テキスト  
                "href")
t_item.get( tex  href =   {})
       tations", .get("annoxt_item= tes ionotatnn   a         ")
 "",_textet("plaintem.gext_iext = tn_tai       pl
     a:ch_text_datm in riext_itefor t         
       ts = []
lt_par       resu       
 "
 eturn "       r     _data:
 rich_textif not
        ""のテキストを抽出"kdown形式トデータからMarリッチテキス  """
      > str:Any]]) -[str, ct List[Ditext_data:ch_t(self, rifrom_contench_text_tract_ri _ex  
    def)
  taich_text_da_content(r_text_fromct_richtra._exturn self        re [])
ext",ch_t"rintent.get(ock_coa = bldatch_text_
        ri, {})ock_typet(blgeent.cont= block.t _contenock bl"
       トを抽出""ブロックからリッチテキス     """:
    -> strype: str)k, block_ttionBlocNoelf, block: ck(srom_bloxt_fich_tet_rracdef _ext 
    
   e} -->"ypock.tなブロック: {bl!-- 不明"<  return f   
           else:    }")
.typeイプ: {blockトされていないブロックタ(f"サポーrrorse ValueE rai     
      error":y == "f strateg       eli"
 -->ポートされていません ロックはサ}ブpeck.ty警告: {blorn f"<!--   retu  
        }") {block.typeクタイプ:トされていないブロッng(f"サポーer.warnilogg      self.
      arning":== "wif strategy        el->"
 e} -: {block.typないブロックれてい!-- サポートさf"<return            :
 older""placehgy == elif strate        eturn None
           r"skip":
 = rategy =if st        
    e)
    k.typ(blocegyion_stratget_conversnfig.lf.cotrategy = se
        s"""ロックの処理いないブポートされて""サ   "
     onal[str]:k) -> Opti NotionBlocock:(self, blockbld_portee_unsup _handl   def
    
 content}"tion_ap f"🎥 {clseeo_url evid})" if url({video_}]動画'e 'ent elsntf caption_cotent icaption_con f"🎥 [{urnret            
      else:t}"
  _contentioncap"🎥 {rl else f_uif video})" video_url '動画'}]({elset n_contennt if captioption_contecaf"🎥 [{turn  re           
    :se    el     rl})"
   ideo_uo_url})]({v({vide'動画'}]else tent on_conent if captiaption_cont f"[![{crntu        re        ポート）
ーでサrkdownプロセッサ一部のMaown（arkdTube埋め込み用のM  # You           url:
   eo_e" in vid.bor "youtuideo_url om" in vyoutube.c"f       i    imeoなど）
  YouTube、V # 埋め込み対応（        alse):
   os", F"embed_videvideo", tting("block_seonfig.get_f.cf sel
        iンクとして表示め込みまたはリ# 設定に応じて埋   
          
   ])["caption"datantent(video__coext_fromract_rich_txt self._eontent =  caption_c      
    on"):"capti.get(ta if video_da"
       t = "n_contentiocap        ションの取得
   # キャプ   
     
     )", "").get("url", {}.get("filevideo_data = rl video_u         
  ":file) == "t("type"ge_data.  elif video
      "")("url", l", {}).get"externao_data.get(o_url = vide        vide":
    ernal") == "ext.get("typeatadeo_d       if vi= ""
 video_url 
        画URLの取得     # 動       
   
  {})",t("videoent.geck.contata = bloeo_did      v変換"""
  ロックの画ブ """動     str:
  ) -> tionBlockck: Noblok(self, o_blocconvert_videdef _    
    "
y_name}f"📎 {displaeturn     r  :
         else"
     _url})leme}]({fi[{display_naeturn f"📎          rl:
     if file_ur
         _name
     e filecontent elsption_nt if cacontetion__name = capisplay     d
   
        on"])ti["capdatatent(file_rom_con_text_fact_rich= self._extrt tion_conten cap           aption"):
("cta.get file_da      if ""
  t =ontenon_c capti     プションの取得
  キャ
        #     ァイル"
    l else "フ_ur] if file")[-1"/t(.splirlle_ue = file_nam    fi     lse:
          eame"]
 data["nle_e_name = fi    fil        ame"):
.get("ne_dataf fil       i ファイル名の取得
        #   
 "")
     "url", et(e", {}).gget("fil file_data.l =   file_ur      ile":
   "f") == typeta.get("le_dalif fi    e"")
    l", ("ur).get{}", xternal.get("eta_da = file    file_url
        ":nal) == "exter"type"t(_data.ge file
        if"
         = "ile_name f""
       rl = _ufile       ルURLの取得
 # ファイ       
    , {})
     et("file"ent.glock.contdata = b  file_"
      換""イルブロックの変   """ファtr:
     -> sionBlock) Not block: lf,le_block(set_fidef _conver
    
    ーク"lse "🔖 ブックマ e" if urln f"🔖 {url}retur         :
       se el          tent}"
 {caption_conlse f"🔖 " if url e{url})_content}]([{captionurn f"🔖          rett:
       ion_conten     if capt       :
  else
      ontentption_clse carl e u if}]({url})"_textinkrn f"[{l  retu        else url
  on_content tient if capcaption_conttext = link_   :
         ", True)tle_as_text "use_timark",ing("book_block_settf.config.getel if s  
     応じて表示方法を変更定に   # 設    
     
    caption"])ata["k_darnt(bookmntefrom_cot_rich_text__extractent = self.oncaption_c    ):
        tion"("capa.getdat bookmark_        if    
    t = ""
enption_cont     ca   ", "")
.get("urlrk_datakma url = boo)
       ", {}kmark"boontent.get( = block.cork_datakma boo    換"""
   マークブロックの変"ブック     ""r:
    -> stck)lonBock: Notio(self, bl_block_bookmarkdef _convert
    on}"
    pressi"数式: {ex   return f         
e:     els   ession)
.format(exprmatck_forn blotur  re          \n$$")
"$$\n{}_format", , "block"uationting("eqlock_set_bg.getlf.confirmat = seck_fo        blo   ions:
 _equatfig.convertf self.con
        iで出力に応じてLaTeX形式  # 設定
      "
        rn "retu          ression:
   if not exp  
       ")
      on", "siget("expresta.ation_dasion = equ  expres
      ", {})"equationget(k.content.= blocn_data io     equat""
   式ブロックの変換"     """数r:
   Block) -> stck: Notionlf, bloock(seon_blert_equaticonvf _  
    deent}**"
  {text_contrn f"**    retu     lse:
     e"
      ails>det-->\n\n</表示されます ツはここに-- 子コンテンn<!mmary>\n\ontent}</su{text_c<summary>attr}>\ns{open_tailn f"<de      retur     se ""
  elultfaexpand_by_deif " en op_attr = "   open  
       False)ult", fa_deby"expand_", ng("toggleock_settit_blconfig.ge = self.by_default expand_
           g", True):_details_tale", "useg("toggttint_block_self.config.ge       if se
 じて変換方法を変更    # 設定に応
    )
        gle"k, "togoc(blckt_from_bloich_texract_rextelf._ent = s_cont  text"
      """トグルブロックの変換  ""      str:
 nBlock) ->block: Notioblock(self, ggle_t_toconver   def _"
    
  " |_contents) +join(cell ". | + "turn "| "re
        テーブル行として出力down# Mark       
 )
        extend(cell_tontents.app   cell_c
         cell_text) else s", Trueape_pipee", "esc("tablingttget_block_se.config.elf s if")"\\|("|", t.replacet = cell_texell_tex  c         プ文字をエスケープ
   # パイ    )
      (cellom_contentich_text_frtract_r = self._exl_text       cel  s:
   n celll i    for cel= []
    ents nt_coll
        ce抽出各セルの内容を#         
        
 return ""        
    not cells:       if      
 )
  ells", []"ct(w_data.gee_rols = tablel c})
       , {able_row"ent.get("t block.contow_data =     table_r   ""
の変換""テーブル行ブロック     ""str:
   Block) ->  Notion block:block(self,t_table_row_nver    def _co  
""
     return 
     では空文字を返すため、ここロックで行われる子ブ    # 実際の変換はンテナ
    e_row）を持つコブロック（tablーブルブロック自体は子       # テ
 ""変換""テーブルブロックの ""      ) -> str:
 ionBlockNotck: ck(self, blort_table_bloef _conve 
    d"画像"
   e_url else magurl})" if i像]({image_eturn f"[画       r      e:
   ls  e
          "ion_content}画像: {capt"_url else fgef imarl})" ige_u]({imant}nte{caption_co画像: "[urn fret              t:
  ntencaption_co        if     合はリンクとして表示
い場ダウンロードしな 画像を #    
       e:        else_url})"
ag_text}]({imn f"![{alt       retur
     else "画像"on_content ptiontent if ca= caption_clt_text  a        _url:
   es and imageimagg.convert_f.confi      if sel更
  て処理方法を変 # 設定に応じ       
        
ion"])captmage_data["ent(it_from_contact_rich_tex= self._extrontent n_c  captio
          "):ionget("captta.image_da     if "
    = "tentcaption_con    取得
     キャプションの 
        #  ")
      "get("url",}).", {fileet("ge_data.grl = ima    image_u       :
 = "file"("type") =_data.get imagelif     e"")
   ", l{}).get("ur, al"tern.get("ex image_dataage_url =  im
          ":nalter== "ex") t("typemage_data.gef i      i""
  e_url =     imag    Lの取得
     # 画像UR 
        
  {})mage", tent.get("i= block.condata    image_"
     ロックの変換"""""画像ブ      :
  ck) -> str NotionBlo, block:k(selfge_blocma _convert_i
    def"
    ntent}\n```ext_co{tanguage}\nmalized_lor"```{neturn f, languagewer(): "kotlin"lin"": "swswift    "t": "rustus    "r",a"jav: va" "jayt"p": nipt" "typescript":escr "javaascript":"javp = {age_ma化# 言語の正規ge", guaa.get("lane_dat coduage =g", ("codeontent.getock.ce_data = blod    clock) -> stionB block: Notf,ブロックの変換""り線切> str:lock) -k: NotionBocelf, blon_tex else ictrip()ent.s text_cont" if_content}te"> {icon_ fp() elsetricontent.st_ex**" if text_content}xt} **{t_teicon"> { True):e_format",uot"use_qallout", tting("ct_block_seg.gefielf.contexicon_"💡"= xt te"📎_text = icon   🔗"ex "💡")moji", con.get("e = i == "emtype")et("co= ""_text n {on",a.get("ic callout_dat =_text", [ich("rut_data.getalloent(crom_contt_fch_texact_rixtrallout","cnt.get(""クの変換アウトブロッル ->k)Blocion: Not(self, blockallout_blockconvert_c_ip() else "strntent." if text_cocontent}t_{texurn f"> クの変ロッ用ブ"引    ""nBlock) -> sotio
    
    def _generate_filename(self, page: NotionPage, pattern: str) -> str:
        """
        ファイル名を生成
        
        Args:
            page: NotionPageオブジェクト
            pattern: ファイル名パターン
            
        Returns:
            生成されたファイル名
        """
        try:
            # 利用可能な変数
            variables = {
                "title": page.title,
                "id": page.id,
                "date": page.created_time.strftime("%Y-%m-%d") if page.created_time else "unknown"
            }
            
            # パターンを適用
            filename = pattern.format(**variables)
            
            # ファイル名をサニタイズ
            safe_filename = MarkdownFile.sanitize_filename(filename)
            
            # 拡張子を追加
            if not safe_filename.endswith('.md'):
                safe_filename += '.md'
            
            return safe_filename
            
        except Exception as e:
            self.logger.warning(f"ファイル名生成エラー: {str(e)}")
            # フォールバック: ページIDを使用
            return f"{page.id}.md"
    
    def get_conversion_summary(self, results: List[MarkdownConversionResult]) -> Dict[str, Any]:
        """
        変換結果のサマリーを取得
        
        Args:
            results: MarkdownConversionResultオブジェクトのリスト
            
        Returns:
            サマリー辞書
        """
        total_files = len(results)
        successful_files = len([r for r in results if not r.has_issues()])
        files_with_warnings = len([r for r in results if r.warnings])
        files_with_unsupported = len([r for r in results if r.unsupported_blocks])
        
        total_size = sum([r.markdown_file.get_file_size() for r in results])
        total_words = sum([r.markdown_file.get_word_count() for r in results])
        
        return {
            "total_files": total_files,
            "successful_files": successful_files,
            "files_with_warnings": files_with_warnings,
            "files_with_unsupported": files_with_unsupported,
            "success_rate": (successful_files / total_files * 100) if total_files > 0 else 0,
            "total_size_mb": total_size / (1024 * 1024),
            "total_words": total_words,
            "average_file_size": total_size / total_files if total_files > 0 else 0,
            "average_words_per_file": total_words / total_files if total_files > 0 else 0,
            "conversion_config": {
                "database_mode": self.config.database_mode,
                "column_layout": self.config.column_layout,
                "unsupported_blocks": self.config.unsupported_blocks,
                "quality_level": self.config.quality_level
            }
        }