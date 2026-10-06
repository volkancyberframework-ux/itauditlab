from django import forms


class InformationPagesWidget(forms.Textarea):
    def __init__(self, attrs=None):
        super().__init__({'class': 'grc-information-pages', 'rows': 12, **(attrs or {})})

    class Media:
        js = ('mobile_api/information_pages.js',)
        css = {'all': ('mobile_api/information_pages.css',)}
