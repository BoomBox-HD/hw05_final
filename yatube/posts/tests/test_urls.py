from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='auth',
            first_name='first',
            last_name='last',
            email='auth@ya.ru'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            pub_date='тест даты',
            group=cls.group
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)

    def test_urls_pages(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': '/group/test-slug/',
            'posts/profile.html': '/profile/auth/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_page_404(self):
        response = self.guest_client.get('/qwer1245/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_add_comment(self):
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/comment/',
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_anon_user_url(self):
        response = self.guest_client.get('/profile/auth/', follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_anon_user_edit_post(self):
        response = self.guest_client.get('/posts/2/edit/')
        self.assertRedirects(response,
                             '/auth/login/?next=' + '/posts/2/edit/')

    def test_new_page_not_login_user(self):
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_new_page_not_login_user(self):
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_new_page_login_user(self):
        response = self.authorized_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_new_page_not_login_user_redirect(self):
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')
