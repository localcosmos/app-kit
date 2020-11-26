from localcosmos_server.online_content.parser import TemplateParser

from .CMSTags import CMSTag

class FactSheetTemplateParser(TemplateParser):

    def __init__(self, meta_app, fact_sheet):

        self.meta_app = meta_app
        
        self.fact_sheet = fact_sheet
        self.template = self.fact_sheet.get_template(self.meta_app)

        self.cms_tags = []
        

    def get_cms_tag(self, microcontent_category, microcontent_type, *tag_content, **tag_kwargs):

        cms_tag = CMSTag(self.fact_sheet, microcontent_category, microcontent_type, *tag_content, **tag_kwargs)

        return cms_tag

