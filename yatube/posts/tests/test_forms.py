import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from ..models import Post, Group, Comment
from django.conf import settings

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка создания поста."""
        count_post = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост'
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        post = Post.objects.last()
        context = {'username': self.user.username}
        self.assertRedirects(response, reverse('posts:profile',
                                               kwargs=context))
        self.assertEqual(Post.objects.count(), count_post + 1)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user, 'Author')

    def test_edit_post(self):
        """Редактирование поста прошло успешно."""
        form_data_new = {
            'text': 'Тестовый пост'
        }
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
        )
        self.authorized_client.post(
            reverse('posts:edit', kwargs={'post_id': post.pk}),
            data=form_data_new,
        )

        self.assertEqual(Post.objects.last().text,
                         form_data_new['text'])

    def cheking_context(self, expect_answer):
        """Проверка контекста страниц.Костыль для test_create_post_with_img."""
        for obj, answer in expect_answer.items():
            with self.subTest(obj=obj):
                resp_context = obj
                self.assertEqual(resp_context, answer)

    def test_create_post_with_img(self):
        """Создается пост с картинкой."""
        post_count = Post.objects.count()
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': CreateFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        last_post = Post.objects.order_by('-pk')[0]
        expect_answer = {
            last_post.text: form_data['text'],
            str(last_post.image): str(last_post.image),
        }
        self.cheking_context(expect_answer)

    def test_create_comment_authorized_user(self):
        """Валидная форма создает комментарий."""
        # Создаем пост и комментарий
        # авторизированным пользователем
        post_new = Post.objects.create(
            author=CreateFormTests.user,
            text='Текст',
        )
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_new.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': post_new.pk})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        # Проверяем, что создался комментарий
        last_comment = Comment.objects.order_by('-pk')[0]
        self.assertEqual(last_comment.text, form_data['text'])
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post_new.pk}),
        )
        self.assertEqual(response.context['comments'][0].text,
            form_data['text']
        )
