from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, Follow, PostForm
from .models import Group, Post, User

TEN = 10


def authorized_only(func):
    # Функция-обёртка в декораторе может быть названа как угодно
    def check_user(request, *args, **kwargs):
        # В любую view-функции первым аргументом передаётся объект request,
        # в котором есть булева переменная is_authenticated,
        # определяющая, авторизован ли пользователь.
        if request.user.is_authenticated:
            # Возвращает view-функцию, если пользователь авторизован.
            return func(request, *args, **kwargs)
        # Если пользователь не авторизован — отправим его на страницу логина.
        return redirect('/auth/login/')
    return check_user


def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    template = 'posts/index.html'
    # Если порядок сортировки определен в классе Meta модели,
    # запрос будет выглядить так:
    # post_list = Post.objects.all()
    # Показывать по 10 записей на странице.
    paginator = Paginator(post_list, TEN)

    # Из URL извлекаем номер запрошенной страницы - это значение параметра page
    page_number = request.GET.get('page')

    # Получаем набор записей для страницы с запрошенным номером
    page_obj = paginator.get_page(page_number)
    # Отдаем в словаре контекста
    context = {
        'page_obj': page_obj,
    }
    cache.clear()
    return render(request, template, context)


def group_post(request, slug):
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    posts = Post.objects.filter(group=group).order_by('-pub_date')
    paginator = Paginator(posts, TEN)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    text = 'Здесь будет информация о группах проекта Yatube'
    context = {
        'group': group,
        'posts': posts,
        'text': text,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    # Здесь код запроса к модели и создание словаря контекста
    author = get_object_or_404(User, username=username)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            author=author,
            user=request.user).exists()
    else:
        following = False
    posts = Post.objects.filter(author=author).order_by("-pub_date").all()
    paginator = Paginator(posts, TEN)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    template = 'posts/profile.html'
    context = {
        'author': author,
        'posts': posts,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    # Здесь код запроса к модели и создание словаря контекста
    post = get_object_or_404(Post, id=post_id)
    template = 'posts/post_detail.html'
    form = CommentForm(request.POST or None)
    post_count = Post.objects.filter(author=post.author).count()
    comments = post.comments.all()
    context = {
        'post': post,
        'post_count': post_count,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


@login_required
def post_create(request):
    btn = 'Добавить'
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None,
                    files=request.FILES or None,)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', username=request.user.username)
    form = PostForm()
    context = {
        'form': form,
        'btn': btn
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    btn = 'редактировать'
    post = get_object_or_404(Post, id=post_id)
    template = 'posts/update_post.html'
    is_edit = True
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(data=request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': is_edit,
        'btn': btn
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    # Получите пост
    template = 'posts:post_detail'
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect(template, post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    user = request.user
    posts_list = Post.objects.filter(author__following__user=user)
    paginator = Paginator(posts_list, TEN)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    """View функция для подписки на автора."""
    template = 'posts:follow_index'
    follow_author = get_object_or_404(User, username=username)
    follow_user = get_object_or_404(User, username=request.user)
    if follow_user != follow_author:
        Follow.objects.get_or_create(
            author=follow_author,
            user=follow_user,
        )
    return redirect(template)


@login_required
def profile_unfollow(request, username):
    """View функция для отписки от автора."""
    template = 'posts:follow_index'
    follow_author = get_object_or_404(User, username=username)
    follow_user = get_object_or_404(User, username=request.user)
    if follow_user != follow_author:
        Follow.objects.get(
            author=follow_author,
            user=follow_user,
        ).delete()
    return redirect(template)
