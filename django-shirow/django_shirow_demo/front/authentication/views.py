from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django_shirow.shirow import create_token_if_needed
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect


@create_token_if_needed
def dashboard(_request):
    pass


def submit(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        dashboard(request)
    return redirect('/')


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'
