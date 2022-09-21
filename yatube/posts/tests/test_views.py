import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django import forms
from posts.models import Group, Post, Follow
from django.conf import settings
from django.core.cache import cache

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()

TEMLATES_PAGES = {
    reverse('posts:index'): 'posts/index.html',
    (reverse('posts:group_list', kwargs={'slug': 'test_slug'})):
        'posts/group_list.html',
    (reverse('posts:profile', kwargs={'username': 'author'})):
        'posts/profile.html',
}

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')

        cls.group = Group.objects.create(
            title='Тестовое название группы',
            description='Тестовое описание группы',
            slug='test_slug',
        )

        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый пост',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
    
    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.clients = {
            'guest_client': self.guest_client,
            'authorized_client': self.authorized_client,
        }

    def test_pages_uses_correct_template(self):
        """URL-адрес использует корректный шаблон."""
        cache.clear()
        templates_url_address = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:group_list', kwargs={'slug': f'{self.group.slug}'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': f'{self.author.username}'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': f'{self.post.id}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:edit', kwargs={'post_id': f'{self.post.id}'}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_url_address.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_posts_list_page_show_correct_context(self):
        cache.clear()
        first_obj = 0
        for reverse_name, template in TEMLATES_PAGES.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][first_obj]
                self.assertEqual(first_object.text,
                                 'Тестовый пост',
                                 f'page_obg неверно передается в {template}')
                self.assertEqual(first_object.group.title,
                                 'Тестовое название группы',
                                 f'page_obg неверно передается в {template}')

    def test_posts_correct_context_post_detail(self):
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        first_object = response.context['post']
        self.assertEqual(first_object.text,
                         'Тестовый пост',
                         f'post неверно передается в {response}')
        self.assertEqual(first_object.group.title,
                         'Тестовое название группы',
                         f'post неверно передается в {response}')

    def test_posts_correct_context_post_edit(self):
        response = self.authorized_client.get(
            reverse('posts:edit', kwargs={'post_id': self.post.id}))
        first_object = response.context['post']
        self.assertEqual(first_object.text,
                         'Тестовый пост',
                         f'post неверно передается в {response}')
        self.assertEqual(first_object.group.title,
                         'Тестовое название группы',
                         f'post неверно передается в {response}')

    def checking_context(self, expect_answer):
        """Проверка контекста страниц"""
        for obj, answer in expect_answer.items():
            with self.subTest(obj=obj):
                resp_context = obj
                self.assertEqual(resp_context, answer)

    def test_new_post_create_correct_with_img(self):
        """Правильное отражение нового поста с картинкой."""
        cache.clear()
        self.auth_client = Client()
        self.auth_client.force_login(self.author)
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded = SimpleUploadedFile(
            name="small.gif", content=small_gif, content_type="image/gif"
        )
        post_new = Post.objects.create(
            author=PostPagesTests.author,
            text="Текст",
            group=PostPagesTests.group,
            image=uploaded,
        )
        # Post_detail отображается корректно
        response = self.auth_client.get(
            reverse("posts:post_detail", kwargs={"post_id": f"{int(post_new.pk)}"})
        )
        expect_answer = {
            response.context["post"].pk: post_new.pk,
            str(response.context["post"]): post_new.text,
            response.context["user"]: post_new.author,
            response.context["post"].image: post_new.image,
        }
        self.checking_context(expect_answer)
        # Пост на index отображается корректно
        response = self.auth_client.get(reverse("posts:index"))
        first_obj = response.context["page_obj"][0]
        obj_auth_0 = first_obj.author
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        obj_img = first_obj.image
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_auth_0: post_new.author,
            obj_img: post_new.image,
        }
        self.checking_context(expect_answer)

        # Пост на странице группы отображается корректно
        response = self.auth_client.get(
            reverse(
                "posts:group_list", kwargs={"slug": f"{PostPagesTests.group.slug}"}
            )
        )
        first_obj = response.context["page_obj"][0]
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        obj_img = first_obj.image
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_img: post_new.image,
        }
        self.checking_context(expect_answer)

        # Пост на странице автора отображается корректно
        response = self.auth_client.get(
            reverse("posts:profile", kwargs={"username": f"{PostPagesTests.author}"})
        )
        first_obj = response.context["page_obj"][0]
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        obj_img = first_obj.image
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_img: post_new.image,
        }
        self.checking_context(expect_answer)

    def test_index_page_include_cashe(self):
        """Шаблон index сформирован с кешем."""
        new_post = Post.objects.create(
            author=PostPagesTests.author,
            text="Текст для теста кеширования.",
        )
        # Проверка views на кеширование
        cache.clear()
        response_with = self.client.get(reverse("posts:index"))
        self.assertIn(new_post, response_with.context["page_obj"])
        new_post.delete()
        response_without = self.client.get(reverse("posts:index"))
        self.assertEqual(response_with.content, response_without.content)


class FollowTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author')
        self.user = User.objects.create_user(username='user')

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_user_subscribe_unsubscribe(self):
        """Пользователь может подписываться."""
        self.assertFalse(self.user.follower.exists())
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={"username": self.author.username}
            )
        )
        self.assertEqual(self.user.follower.first().author, self.author)

    def test_authorized_user_unsubscribe(self):
        """Пользователь может отписаться."""
        Follow.objects.create(user=self.user, author=self.author)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={"username": self.author.username}
            )
        )
        self.assertFalse(self.user.follower.exists())
    
    def test_new_post_shown_in_feed_subscriber(self):
        """Пост появляется в ленте подписанного пользователя."""
        Follow.objects.create(user=self.user, author=self.author)
        post = Post.objects.create(
            text='Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
            author=self.author,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(post, response.context.get('page_obj').object_list)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.author = User.objects.create_user(username='test')
        cls.slug = 'test'
        group = Group.objects.create(
            title='Тестовая группа',
            slug=cls.slug,
            description='Тестовое описание',
        )
        for i in range(13):
            Post.objects.create(
                author=cls.author,
                text='Тестовый пост',
                group=group,
            )
        super().setUpClass()

    def test_paginator(self):
        cache.clear()
        context = {'username': self.author.username}
        url_names = {
            reverse('posts:index'): 10,
            reverse('posts:index') + '?page=2': 3,
            reverse('posts:profile',
                    kwargs=context): 10,
            reverse('posts:profile',
                    kwargs=context) + '?page=2': 3,
            reverse('posts:group_list',
                    kwargs={'slug': self.slug}): 10,
            reverse('posts:group_list',
                    kwargs={'slug': self.slug}) + '?page=2': 3,
        }
        for adress, count in url_names.items():
            response = self.client.get(adress)
            amount = len(response.context['page_obj'])
            self.assertEqual(amount, count)
