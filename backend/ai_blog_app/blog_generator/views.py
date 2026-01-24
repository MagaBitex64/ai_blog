from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from groq import Groq
from pytubefix import YouTube
import os
import assemblyai as aai
from groq import Groq
from .models import BlogPost
# Create your views here.
@login_required()
def index(request):
    return render(request, 'index.html')
@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'errorMessage': 'Invalid data sent'}, status=400)


        title = yt_title(yt_link)
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': 'failed to get transcript'}, status=500)


        #use openai tp generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': 'failed to get blog content'}, status=500)
        #save blog article in database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content
        )
        new_blog_article.save()

        #return blog article as response
        return JsonResponse({'content': blog_content}, status=200)
    else:
        return JsonResponse({'errorMessage': 'Invalid Request Method'}, status=405)


def yt_title(link):
    yt = YouTube(
        link,
        use_oauth=False,
        allow_oauth_cache=True)
    return yt.title

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "abb279f07a894812b227e32d02cc541d"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    return transcript.text

def generate_blog_from_transcription(transcription):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    prompt = f" Based on the following transcription from a Youtube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n {transcription}\n\n Article:"
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role":"system",
                "content":(
                    "You are a professional blog writer. "
                    "Output ONLY clean plain text. "
                    "Do NOT use markdown, headings symbols, bullet points, tables, bold, italics, or quotes. "
                    "Use normal paragraphs only."
                )
            },
            {
                "role":"user",
                "content":prompt
            }
        ],
        model = "groq/compound"
    )
    generated_content = chat_completion.choices[0].message.content
    return generated_content

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file


def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request,'blog-details.html',{'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request,"all-blogs.html",{'blog_articles':blog_articles})
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username and/or password.'
            return render(request, 'login.html', {'errorMessage': error_message})
    return render(request, 'login.html')
def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']
        if password == repeatPassword:
            pass
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error account creation'
                return render(request, 'signup.html', {'errorMessage': error_message})
        else:
            error_message = 'Passwords do not match'
            return render(request, 'signup.html', {'errorMessage': error_message})
    return render(request, 'signup.html')
def user_logout(request):
    logout(request)
    return redirect('/')
