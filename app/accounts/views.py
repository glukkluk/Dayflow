from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import (
    AvatarForm,
    DeleteAccountForm,
    ProfileForm,
    RegistrationForm,
    UsernameForm,
)


class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("planner:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = authenticate(
            self.request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password1"],
        )
        if user is not None:
            login(self.request, user)
        messages.success(self.request, "Обліковий запис створено. Вітаємо!")
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """One page with several independent forms; ``action`` says which was sent."""

    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_forms(self, action=None, data=None, files=None):
        """Build every form; only the submitted one is bound to POST data."""
        user = self.request.user

        def bind(name, form_class, *args, **kwargs):
            if action == name:
                return form_class(*args, data=data, files=files, **kwargs)
            return form_class(*args, **kwargs)

        return {
            "settings_form": bind("settings", ProfileForm, instance=user.profile),
            # A fresh instance: a rejected username must not leak into the header.
            "username_form": bind(
                "username",
                UsernameForm,
                instance=get_user_model().objects.get(pk=user.pk),
                prefix="username",
            ),
            "avatar_form": bind("avatar", AvatarForm, prefix="avatar"),
            "password_form": bind("password", PasswordChangeForm, user, prefix="pw"),
            "delete_form": bind("delete", DeleteAccountForm, user, prefix="del"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for name, form in self.get_forms().items():
            context.setdefault(name, form)
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "avatar_remove":
            if request.user.profile.avatar:
                request.user.profile.avatar.delete(save=True)
            messages.success(request, "Аватар видалено.")
            return redirect(self.success_url)

        forms = self.get_forms(action, request.POST, request.FILES)
        form = forms.get(f"{action}_form")
        if form is None:
            return redirect(self.success_url)
        if not form.is_valid():
            context = self.get_context_data(
                active_action=action, **{f"{action}_form": form}
            )
            return self.render_to_response(context)

        if action == "delete":
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Акаунт і всі ваші дані видалено.")
            return redirect("accounts:login")
        if action == "avatar":
            form.save(request.user.profile)
            messages.success(request, "Аватар оновлено.")
        elif action == "password":
            user = form.save()
            update_session_auth_hash(request, user)  # keep the user signed in
            messages.success(request, "Пароль змінено.")
        else:
            form.save()
            messages.success(
                request,
                {
                    "settings": "Налаштування профілю збережено.",
                    "username": "Ім'я користувача змінено.",
                }[action],
            )
        return redirect(self.success_url)
