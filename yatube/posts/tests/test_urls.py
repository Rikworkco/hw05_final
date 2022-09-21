from filecmp import clear_cache
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.cache import cache
from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            description='тестовое описание группы',
            slug='test_slug',
        )

        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.clients = {
            'guest_client': self.guest_client,
            'authorized_client': self.authorized_client,
        }

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        templates_url_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/create_post.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_available_to_any_client(self):
        """URL-адрес доступен любому пользователю."""
        url_address = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.author.username}/',
            f'/posts/{self.post.id}/',
        ]
        for client in self.clients:
            for address in url_address:
                with self.subTest(client=client, address=address):
                    response = self.clients[client].get(address)
                    self.assertEqual(response.status_code, 200)

    def test_urls_available_to_auth_client(self):
        """Адреса, доступные авторизованному пользователю."""
        urls = [
            '/create/',
            f'/posts/{self.post.id}/edit/',
        ]
        clients = [
            'guest_client',
            'authorized_client',
        ]
        for url in urls:
            for client in clients:
                with self.subTest(url=url):
                    response = self.clients[client].get(url, follow=True)
                    self.assertEqual(response.status_code, 200)

    def test_url_avaliable_to_auth_for_edit(self):
        """Редактирование доступно авторизованному пользователю."""
        response = self.authorized_client.get(reverse(
            'posts:edit', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_404(self):
        """Cервер возвращает код 404, если страница не найдена."""
        response = self.guest_client.get('/notfound/')
        self.assertEqual(response.status_code, 404)
