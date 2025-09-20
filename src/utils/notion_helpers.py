"""
Notion-specific utility functions
"""


def make_notion_page_url(page_id, url_root):
    """Returns a URL to the Notion page"""
    url_id = page_id.replace('-', '')
    return url_root + url_id


def make_description(rich_text):
    """Returns a plain text description from Notion's rich text field"""
    description = ""
    for item in rich_text:
        description += item['text']['content']
    return description


def make_one_line_plain_text(rich_text):
    """Returns a single line of plain text from Notion's rich text field"""
    return rich_text[0]['plain_text']


def make_link(rich_text):
    """Returns a list with format: [Display text, URL]"""
    return [rich_text[0]['text']['content'], rich_text[0]['text']['link']['url']]