from django import forms

class TextAnalysisForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea, required=False , label="Введите текст")
    file = forms.FileField(required=False, label="Или загрузите файл (txt, docx)")
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('text') and not cleaned_data.get('file'):
            raise forms.ValidationError("Введите текст или загрузите файл")
        return cleaned_data