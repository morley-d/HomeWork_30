import json

from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated

from ads.models import Category, Ad, Selection
from ads.permissions import SelectionUpdatePermission, AdUpdatePermission
from ads.serializers import SelectionListSerializer, SelectionDetailSerializer, SelectionSerializer, AdDetailSerializer, \
    AdSerializer
from users.models import User


def root(request):
    return JsonResponse({
        "status": "ok"
    })


class SelectionListView(ListAPIView):
    queryset = Selection.objects.all()
    serializer_class = SelectionListSerializer


class SelectionRetrieveView(RetrieveAPIView):
    queryset = Selection.objects.all()
    serializer_class = SelectionDetailSerializer


class SelectionCreateView(CreateAPIView):
    queryset = Selection.objects.all()
    serializer_class = SelectionSerializer
    permission_classes = [IsAuthenticated]


class SelectionUpdateView(UpdateAPIView):
    queryset = Selection.objects.all()
    serializer_class = SelectionSerializer
    permission_classes = [IsAuthenticated, SelectionUpdatePermission]


class SelectionDeleteView(DestroyAPIView):
    queryset = Selection.objects.all()
    serializer_class = SelectionSerializer
    permission_classes = [IsAuthenticated, SelectionUpdatePermission]


class CategoryView(ListView):
    models = Category
    queryset = Category.objects.all()

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        self.object_list = self.object_list.order_by("name")

        response = []
        for category in self.object_list:
            response.append({
                "id": category.id,
                "name": category.name,
            })

        return JsonResponse(response, safe=False)


class CategoryDetailView(DetailView):
    model = Category

    def get(self, request, *args, **kwargs):
        try:
            category = self.get_object()
        except Http404:
            return JsonResponse({"error": "Category not found"}, status=404)

        return JsonResponse({
            "id": category.id,
            "name": category.name,
        })


@method_decorator(csrf_exempt, name='dispatch')
class CategoryCreateView(CreateView):
    model = Category
    fields = ["name"]

    def post(self, request, *args, **kwargs):
        category_data = json.loads(request.body)

        category = Category.objects.create(
            name=category_data["name"],
        )

        return JsonResponse({
            "id": category.id,
            "name": category.name,
        })


@method_decorator(csrf_exempt, name='dispatch')
class CategoryUpdateView(UpdateView):
    model = Category
    fields = ["name"]

    def patch(self, request, *args, **kwargs):
        try:
            super().post(request, *args, **kwargs)
        except Http404:
            return JsonResponse({"error": "Category not found"}, status=404)

        category_data = json.loads(request.body)
        self.object.name = category_data["name"]

        self.object.save()
        return JsonResponse({
            "id": self.object.id,
            "name": self.object.name
        })


@method_decorator(csrf_exempt, name='dispatch')
class CategoryDeleteView(DeleteView):
    model = Category
    success_url = "/"

    def delete(self, request, *args, **kwargs):
        try:
            super().delete(request, *args, **kwargs)
        except Http404:
            return JsonResponse({"error": "Category not found"}, status=404)

        return JsonResponse({"status": "ok"}, status=200)


class AdView(ListView):
    models = Ad
    queryset = Ad.objects.all()

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        categories = request.GET.getlist("cat", [])
        if categories:
            self.object_list = self.object_list.filter(category_id__in=categories)

        if request.GET.get("text", None):
            self.object_list = self.object_list.filter(name__icontains=request.GET.get("text"))

        if request.GET.get("location", None):
            self.object_list = self.object_list.filter(author__locations__name__icontains=request.GET.get("location"))

        if request.GET.get("price_from", None):
            self.object_list = self.object_list.filter(price__gte=request.GET.get("price_from"))

        if request.GET.get("price_to", None):
            self.object_list = self.object_list.filter(price__lte=request.GET.get("price_to"))

        self.object_list = self.object_list.select_related('author').order_by("-price")
        paginator = Paginator(self.object_list, settings.TOTAL_ON_PAGE)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        ads = []
        for ad in page_obj:
            ads.append({
                "id": ad.id,
                "name": ad.name,
                "author_id": ad.author_id,
                "author": ad.author.first_name,
                "price": ad.price,
                "description": ad.description,
                "is_published": ad.is_published,
                "category_id": ad.category_id,
                "image": ad.image.url if ad.image else None,
            })

        response = {
            "items": ads,
            "num_pages": page_obj.paginator.num_pages,
            "total": page_obj.paginator.count,
        }

        return JsonResponse(response, safe=False)


class AdDetailView(RetrieveAPIView):
    # model = Ad
    #
    # def get(self, request, *args, **kwargs):
    #     try:
    #         ad = self.get_object()
    #     except Http404:
    #         return JsonResponse({"error": "Ads not found"}, status=404)
    #
    #     return JsonResponse({
    #         "id": ad.id,
    #         "name": ad.name,
    #         "author_id": ad.author_id,
    #         "author": ad.author.first_name,
    #         "price": ad.price,
    #         "description": ad.description,
    #         "is_published": ad.is_published,
    #         "category_id": ad.category_id,
    #         "image": ad.image.url if ad.image else None,
    #     })
    queryset = Ad.objects.all()
    serializer_class = AdDetailSerializer
    permission_classes = [IsAuthenticated]


@method_decorator(csrf_exempt, name='dispatch')
class AdCreateView(CreateView):
    model = Ad
    fields = ["name", "author", "price", "description", "is_published", "category"]

    def post(self, request, *args, **kwargs):
        ad_data = json.loads(request.body)

        author = get_object_or_404(User, pk=ad_data["author_id"])
        category = get_object_or_404(Category, pk=ad_data["category_id"])

        ad = Ad.objects.create(
            name=ad_data["name"],
            author=author,
            price=ad_data["price"],
            description=ad_data["description"],
            is_published=ad_data["is_published"],
            category=category,
        )

        return JsonResponse({
            "id": ad.id,
            "name": ad.name,
            "author_id": ad.author_id,
            "author": ad.author.first_name,
            "price": ad.price,
            "description": ad.description,
            "is_published": ad.is_published,
            "category_id": ad.category_id,
            "image": ad.image.url if ad.image else None,
        })


@method_decorator(csrf_exempt, name='dispatch')
class AdUpdateView(UpdateAPIView):
    # model = Ad
    # fields = ["name", "author", "price", "description", "category"]
    #
    # def patch(self, request, *args, **kwargs):
    #     try:
    #         super().post(request, *args, **kwargs)
    #     except Http404:
    #         return JsonResponse({"error": "Ads not found"}, status=404)
    #
    #     ad_data = json.loads(request.body)
    #     if ad_data.get("name"):
    #         self.object.name = ad_data["name"]
    #     if ad_data.get("price"):
    #         self.object.price = ad_data["price"]
    #     if ad_data.get("description"):
    #         self.object.description = ad_data["description"]
    #
    #     if ad_data.get("author_id"):
    #         self.object.author = get_object_or_404(User, pk=ad_data["author_id"])
    #     if ad_data.get("category_id"):
    #         self.object.category = get_object_or_404(Category, pk=ad_data["category_id"])
    #
    #     self.object.save()
    #     return JsonResponse({
    #         "id": self.object.id,
    #         "name": self.object.name,
    #         "author_id": self.object.author_id,
    #         "author": self.object.author.first_name,
    #         "price": self.object.price,
    #         "description": self.object.description,
    #         "is_published": self.object.is_published,
    #         "category_id": self.object.category_id,
    #         "image": self.object.image.url if self.object.image else None,
    #     })
    queryset = Ad.objects.all()
    serializer_class = AdDetailSerializer
    permission_classes = [IsAuthenticated, AdUpdatePermission]


@method_decorator(csrf_exempt, name='dispatch')
class AdUploadImageView(UpdateView):
    model = Ad
    fields = ["image"]

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            return JsonResponse({"error": "Ads not found"}, status=404)

        self.object.image = request.FILES.get("image", None)
        self.object.save()

        return JsonResponse({
            "id": self.object.id,
            "name": self.object.name,
            "author_id": self.object.author_id,
            "author": self.object.author.first_name,
            "price": self.object.price,
            "description": self.object.description,
            "is_published": self.object.is_published,
            "category_id": self.object.category_id,
            "image": self.object.image.url if self.object.image else None,
        })


@method_decorator(csrf_exempt, name='dispatch')
class AdDeleteView(DestroyAPIView):
    # model = Ad
    # success_url = "/"
    #
    # def delete(self, request, *args, **kwargs):
    #     try:
    #         super().delete(request, *args, **kwargs)
    #     except Http404:
    #         return JsonResponse({"error": "Ads not found"}, status=404)
    #
    #     return JsonResponse({"status": "ok"}, status=200)
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    permission_classes = [IsAuthenticated, AdUpdatePermission]
