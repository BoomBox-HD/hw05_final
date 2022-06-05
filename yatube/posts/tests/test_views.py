import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..models import Group, Post, Follow
from django import forms
from ..forms import PostForm, Comment
from django.core.cache import cache

User = get_user_model()


class ModelsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            pub_date='тест даты',
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse('posts:index'):
            'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.post.author.username}):
            'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
            'posts/update_post.html',
            reverse('posts:post_create'):
            'posts/create_post.html',
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name,
                                                      follow=True)
                self.assertTemplateUsed(response, template)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(dir=settings.BASE_DIR))
class PagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Текст asldkjas;ldkjas;lkja',
            image=cls.uploaded
        )
        cls.form = PostForm()
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.post,
            author=cls.author,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.user = self.author
        self.authorized_client.force_login(self.user)

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def preparation(self, response):
        response_post = response.context.get('page_obj')[0]
        author = response_post.author
        group = response_post.group
        text = response_post.text
        image = response_post.image
        self.assertEqual(author, self.author)
        self.assertEqual(group, self.group)
        self.assertEqual(text, self.post.text)
        self.assertEqual(image, self.post.image)

    def preparation_group_list_and_profile(self, response):
        response_post = response.context.get('posts')[0]
        author = response_post.author
        group = response_post.group
        text = response_post.text
        image = response_post.image
        self.assertEqual(author, self.author)
        self.assertEqual(group, self.group)
        self.assertEqual(text, self.post.text)
        self.assertEqual(image, self.post.image)

    def preparation_post_detail(self, response):
        response_post = response.context.get('post')
        author = response_post.author
        group = response_post.group
        text = response_post.text
        image = response_post.image
        self.assertEqual(author, self.author)
        self.assertEqual(group, self.group)
        self.assertEqual(text, self.post.text)
        self.assertEqual(image, self.post.image)

    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.preparation(response)

    def test_one_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug':
                                                   self.group.slug}))
        self.preparation_group_list_and_profile(response)

    def test_two_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:profile',
                                           kwargs={'username':
                                                   self.post.author.username}))
        self.preparation_group_list_and_profile(response)

    def test_tre_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:post_detail',
                                           kwargs={'post_id': self.post.id}))
        self.preparation_post_detail(response)

    def test_post_edit_get_correct_context(self):
        post = PagesTests.post
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': post.id}))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], PostForm)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('form').instance.id, post.id)

    def test_post_create_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.author = User.objects.create(username='User')
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Теcт опись',
        )
        cls.posts = []
        for i in range(12):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.author,
                group=cls.group
            )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.user = self.author
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        list_urls = {
            reverse('posts:index'): 'index',
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug'}): 'group_list',
            reverse('posts:profile',
                    kwargs={'username': 'User'}): 'profile',
        }
        for tested_url in list_urls.keys():
            response = self.client.get(tested_url)
            self.assertEqual(len(
                response.context.get('page_obj').object_list), 10)

    def test_second_page_contains_three_records(self):
        list_urls = {
            reverse('posts:index'): 'index',
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug'}): 'group_list',
            reverse('posts:profile',
                    kwargs={'username': 'User'}): 'profile',
        }
        for test_url in list_urls.keys():
            response = self.client.get(test_url + '?page=2')
            self.assertEqual(len(
                response.context.get('page_obj').object_list), 3)


class PostGroupPages(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        cls.author = User.objects.create(username='User')
        cls.post = Post.objects.create(
            text='Текст пост',
            group=cls.group,
            author=cls.author,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.user = self.author
        self.authorized_client.force_login(self.user)

    def test_the_post_was_not_included_in_the_group(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group_2.slug}))
        self.assertEqual(len(response.context.get('page_obj').object_list), 0)


class CacheViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тест опись'
        )
        cls.post = Post.objects.create(
            text='test_post',
            group=cls.group,
            author=cls.author
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.user = self.author
        self.authorized_client.force_login(self.user)

    def test_cache_index(self):
        response = self.guest_client.get(reverse('posts:index'))
        response_1 = self.guest_client.get(reverse('posts:index'))
        Post.objects.create(
            text='тест',
            author=self.user,
        )
        self.assertEqual(response.content, response_1.content)
        cache.clear()
        response_2 = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, response_2.content)


class FollowTests(TestCase):
    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_1 = User.objects.create_user(username='user')
        self.user_2 = User.objects.create_user(username='User')
        self.post = Post.objects.create(
            author=self.user_2,
            text='Тестовая запись для тестирования ленты'
        )
        self.client_auth_follower.force_login(self.user_1)
        self.client_auth_following.force_login(self.user_2)

    def test_follow(self):
        self.client_auth_follower.get(reverse('posts:profile_follow',
                                              kwargs={'username':
                                                      self.user_2.username}))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unfollow(self):
        self.client_auth_follower.get(reverse('posts:profile_follow',
                                              kwargs={'username':
                                                      self.user_2.
                                                      username}))
        self.client_auth_follower.get(reverse('posts:profile_unfollow',
                                      kwargs={'username':
                                              self.user_2.username}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_subscription_feed(self):
        """запись появляется в ленте подписчиков"""
        Follow.objects.create(user=self.user_1,
                              author=self.user_2)
        response = self.client_auth_follower.get('/follow/')
        post_text_0 = response.context['page_obj'][0].text
        self.assertEqual(post_text_0, 'Тестовая запись для тестирования ленты')
        # в качестве неподписанного пользователя проверяем собственную ленту
        response = self.client_auth_following.get('/follow/')
        self.assertNotContains(response,
                               'Тестовая запись для тестирования ленты')
