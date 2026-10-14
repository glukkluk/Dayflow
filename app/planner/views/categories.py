from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..forms import CategoryForm
from ..models import Category


class CategoryOwnerMixin(LoginRequiredMixin):
    model = Category

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)  # ty: ignore[unresolved-attribute]


class CategoryFormMixin(SuccessMessageMixin):
    form_class = CategoryForm
    template_name = "planner/form.html"
    success_url = reverse_lazy("planner:category_list")
    success_message = "Категорію збережено."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # ty: ignore[unresolved-attribute]
        context["cancel_url"] = "planner:category_list"
        return context


class CategoryListView(CategoryOwnerMixin, ListView):
    template_name = "planner/category_list.html"
    context_object_name = "category_list"


class CategoryCreateView(CategoryOwnerMixin, CategoryFormMixin, CreateView):
    extra_context = {"title": "Нова категорія"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Category(user=self.request.user)
        return kwargs


class CategoryEditView(CategoryOwnerMixin, CategoryFormMixin, UpdateView):
    extra_context = {"title": "Редагувати категорію"}


class CategoryDeleteView(CategoryOwnerMixin, DeleteView):
    template_name = "planner/confirm_delete.html"
    success_url = reverse_lazy("planner:category_list")
    extra_context = {
        "title": "Видалити категорію",
        "cancel_url": "planner:category_list",
        "note": "Події та завдання залишаться без категорії.",
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, "Категорію видалено. Події та завдання збережено без категорії."
        )
        return response
