from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View

from .forms import ProfileForm, RegistrationForm


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        form = RegistrationForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        form = RegistrationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Обліковий запис створено. Увійдіть у систему.")
            return redirect("accounts:login")

        return render(request, "accounts/register.html", {"form": form})


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        form = ProfileForm(instance=request.user.profile)
        return render(request, "accounts/profile.html", {"form": form})

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user.profile)

        if form.is_valid():
            form.save()
            messages.success(request, "Налаштування профілю збережено.")
            return redirect("accounts:profile")
        return render(request, "accounts/profile.html", {"form": form})
