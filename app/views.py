from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import TextAnalysisForm
from .models import AnalysisResult
import spacy
from spacy import displacy
import docx
from io import TextIOWrapper
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.http import HttpResponse
from io import StringIO
import stanza
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc
)


DEP_TRANSLATIONS = {
    'acl': 'опред_гл',
    'advcl': 'обст_гл',
    'advmod': 'обст',
    'amod': 'опред',
    'appos': 'прилож',
    'aux': 'вспом',
    'case': 'предлог',
    'cc': 'союз',
    'ccomp': 'изъясн',
    'clf': 'класс',
    'compound': 'состав',
    'conj': 'сочинение',
    'cop': 'связка',
    'csubj': 'подл_гл',
    'dep': 'завис',
    'det': 'детерм',
    'discourse': 'дискурс',
    'dislocated': 'смещ',
    'expl': 'эксплет',
    'fixed': 'фраз',
    'flat': 'плоская',
    'goeswith': 'сочет',
    'iobj': 'косв_доп',
    'list': 'список',
    'mark': 'маркер',
    'nmod': 'мод',
    'nsubj': 'подл',
    'nsubj:pass':'подл баз',
    'nummod': 'числ',
    'obj': 'доп',
    'obl': 'обст_доп',
    'orphan': 'сирота',
    'parataxis': 'парат',
    'punct': 'пункт',
    'reparandum': 'повтор',
    'ROOT': 'корень',
    'vocative': 'зват',
    'xcomp': 'связ_доп'
}

def translate_dep(dep):
    """Переводит английские сокращения зависимостей на русские"""
    return DEP_TRANSLATIONS.get(dep, dep) 

def extract_text_from_file(file):
    if file.name.endswith('.txt'):
        return TextIOWrapper(file, encoding='utf-8').read()
    elif file.name.endswith('.docx'):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

def analyze_text_spacy(request):
    if request.method == 'POST':
        form = TextAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            text = form.cleaned_data['text']
            file = form.cleaned_data.get('file')
            
            if file and not text:
                text = extract_text_from_file(file)
            
            nlp = spacy.load("ru_core_news_sm")
            doc = nlp(text[:10000])
            
            analysis_results = {
                'original_text': text,
                'visualization': displacy.render(doc, style="dep", page=True),
                'morph_analysis': [],
                'entities': []
            }
            
            for token in doc:
                analysis_results['morph_analysis'].append({
                    'text': token.text,
                    'pos': token.pos_,
                    'dep': translate_dep(token.dep_),  # Используем перевод
                    'dep_original': token.dep_,         # Сохраняем оригинал для reference
                    'lemma': token.lemma_
                })
            
            for ent in doc.ents:
                analysis_results['entities'].append({
                    'text': ent.text,
                    'label': ent.label_
                })
            
            # Сохраняем в сессию для неавторизованных пользователей
            request.session['analysis_results'] = analysis_results
            
            # Сохраняем в БД для авторизованных
            if request.user.is_authenticated:
                analysis = AnalysisResult.objects.create(
                    user=request.user,
                    input_text=text[:1000] + "..." if len(text) > 1000 else text,
                    entities=analysis_results['entities'],
                    visualization_html=analysis_results['visualization'],
                    morph_analysis=analysis_results['morph_analysis']
                )
                analysis_id = analysis.id
            else:
                analysis_id = None
            
            return render(request, 'analysis_result.html', {
                'original_text': text,
                'visualization': analysis_results['visualization'],
                'morph_analysis': analysis_results['morph_analysis'],
                'entities': analysis_results['entities'],
                'analysis_id': analysis_id
            })
    else:
        form = TextAnalysisForm()
    
    return render(request, 'analyze.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт {username} создан! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def download_text(request):
    if request.method == 'POST':
        # Получаем текст из сессии (для неавторизованных пользователей)
        text = request.session.get('analysis_text', '')
        
        # Или из БД (для авторизованных)
        if request.user.is_authenticated and 'analysis_id' in request.POST:
            try:
                analysis = AnalysisResult.objects.get(
                    id=request.POST['analysis_id'], 
                    user=request.user
                )
                text = analysis.input_text
            except AnalysisResult.DoesNotExist:
                pass
        
        if not text:
            return HttpResponse("Текст для анализа не найден", status=404)
        
        # Анализ текста
        nlp = spacy.load("ru_core_news_sm")
        doc = nlp(text[:100000])  
        
        
        output = StringIO()
        
        
        output.write("=== ПОЛНЫЙ АНАЛИЗ ТЕКСТА ===\n\n")
        
        
        output.write("=== ИСХОДНЫЙ ТЕКСТ ===\n")
        output.write(text + "\n\n")
        
        
        output.write("=== МОРФОЛОГИЧЕСКИЙ И СИНТАКСИЧЕСКИЙ РАЗБОР ===\n")
        output.write("Формат: Текст | Часть речи | Синтакс. связь | Лемма \n")
        output.write("-"*80 + "\n")
        
        for token in doc:
            line = f"{token.text:15} | {token.pos_:8} | {token.dep_:12} | {token.lemma_:10} \n"
            output.write(line)
        
        # Именованные сущности 
        if hasattr(doc, 'ents') and doc.ents:
            output.write("\n=== ИМЕНОВАННЫЕ СУЩНОСТИ ===\n")
            for ent in doc.ents:
                output.write(f"{ent.text} ({ent.label_})\n")
        
        # Формируем ответ
        response = HttpResponse(
            output.getvalue(),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; filename="text_analysis.txt"'
        return response
    
    return HttpResponse("Метод не разрешен", status=405)

def download_visualization(request):
    if request.method == 'POST':
        html_content = request.POST.get('visualization_html', '')
        
        #Скачать как SVG
        if '<svg' in html_content:
            response = HttpResponse(html_content, content_type='image/svg+xml')
            response['Content-Disposition'] = 'attachment; filename="visualization.svg"'
        
        return response
    return redirect('analyze')



@login_required
def history(request):
    analyses = AnalysisResult.objects.filter(user=request.user).order_by('-analysis_date')
    return render(request, 'history.html', {'analyses': analyses})

@login_required
def view_analysis(request, analysis_id):
    analysis = AnalysisResult.objects.get(id=analysis_id, user=request.user)
    return render(request, 'analysis_result.html', {
        'original_text': analysis.input_text,
        'visualization': analysis.visualization_html,
        'entities': analysis.entities  # Передаём сохранённые сущности
    })


def analyze_text_natasha(request):
    if request.method == 'POST':
        form = TextAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            text = form.cleaned_data['text']
            file = form.cleaned_data.get('file')
            
            if file and not text:
                text = extract_text_from_file(file)
            
            # Инициализация компонентов Natasha
            segmenter = Segmenter()
            morph_vocab = MorphVocab()
            emb = NewsEmbedding()
            morph_tagger = NewsMorphTagger(emb)
            syntax_parser = NewsSyntaxParser(emb)
            ner_tagger = NewsNERTagger(emb)
            
            # Обработка текста
            doc = Doc(text[:10000])  # Ограничение длины текста
            doc.segment(segmenter)
            doc.tag_morph(morph_tagger)
            doc.parse_syntax(syntax_parser)
            doc.tag_ner(ner_tagger)
            
            # Лемматизация
            for token in doc.tokens:
                token.lemmatize(morph_vocab)
            
            # Подготовка результатов
            analysis_results = {
                'original_text': text,
                'tokens': [],
                'entities': [],
                'syntax': []
            }
            
            # Морфологический анализ
            for token in doc.tokens:
                analysis_results['tokens'].append({
                    'text': token.text,
                    'lemma': token.lemma,
                    'pos': token.pos
                })
            
            # Синтаксический анализ
            for token in doc.tokens:
                if token.rel:
                    analysis_results['syntax'].append({
                        'text': token.text,
                        'head': doc.tokens[token.head_id].text if token.head_id else 'ROOT',
                        'rel': token.rel
                    })
            
            # Извлечение сущностей
            for span in doc.spans:
                analysis_results['entities'].append({
                    'text': span.text,
                    'type': span.type,
                    'start': span.start,
                    'stop': span.stop
                })
            
            # Сохранение результатов
            request.session['natasha_analysis'] = analysis_results
            
            if request.user.is_authenticated:
                analysis = AnalysisResult.objects.create(
                    user=request.user,
                    input_text=text[:1000] + "..." if len(text) > 1000 else text,
                    entities=analysis_results['entities'],
                    morph_analysis=analysis_results['tokens'],
                    syntax_analysis=analysis_results['syntax']
                )
                analysis_id = analysis.id
            else:
                analysis_id = None
            
            return render(request, 'natasha_result.html', {
                'results': analysis_results,
                'analysis_id': analysis_id
            })
    
    return render(request, 'analyze.html', {'form': TextAnalysisForm()})




def analyze_text_stanza(request):
    if request.method == 'POST':
        form = TextAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            text = form.cleaned_data['text']
            file = form.cleaned_data.get('file')
            
            if file and not text:
                text = extract_text_from_file(file)
            
            # Загрузка модели Stanza (только при первом вызове)
            stanza.download('ru')
            nlp = stanza.Pipeline('ru', processors='tokenize,pos,lemma,depparse,ner')
            
            # Обработка текста
            doc = nlp(text[:10000])  # Ограничение длины текста
            
            # Подготовка результатов
            analysis_results = {
                'original_text': text,
                'tokens': [],
                'entities': [],
                'dependencies': []
            }
            
            # Морфологический анализ и зависимости
            for sentence in doc.sentences:
                for word in sentence.words:
                    analysis_results['tokens'].append({
                        'text': word.text,
                        'lemma': word.lemma,
                        'pos': word.pos,
                        'feats': word.feats if word.feats else None
                    })
                    
                    analysis_results['dependencies'].append({
                        'text': word.text,
                        'head': sentence.words[word.head-1].text if word.head > 0 else 'ROOT',
                        'deprel': word.deprel
                    })
            
            # Извлечение сущностей
            for ent in doc.ents:
                analysis_results['entities'].append({
                    'text': ent.text,
                    'type': ent.type,
                    'start_char': ent.start_char,
                    'end_char': ent.end_char
                })
            
            # Сохранение результатов
            request.session['stanza_analysis'] = analysis_results
            
            if request.user.is_authenticated:
                analysis = AnalysisResult.objects.create(
                    user=request.user,
                    input_text=text[:1000] + "..." if len(text) > 1000 else text,
                    entities=analysis_results['entities'],
                    morph_analysis=analysis_results['tokens'],
                    dependencies=analysis_results['dependencies']
                )
                analysis_id = analysis.id
            else:
                analysis_id = None
            
            return render(request, 'stanza_result.html', {
                'results': analysis_results,
                'analysis_id': analysis_id
            })
    
    return render(request, 'analyze.html', {'form': TextAnalysisForm()})

