from django.test.client import Client
from askbot.tests.utils import AskbotTestCase
from askbot.conf import settings
from askbot import models

class BadgeTests(AskbotTestCase):

    def setUp(self):
        self.u1 = self.create_user(username = 'user1')
        self.u2 = self.create_user(username = 'user2')
        self.u3 = self.create_user(username = 'user3')
        self.client = Client()

    def assert_have_badge(self, badge_key, recipient = None, expected_count = 1):
        filters = {'badge__slug': badge_key, 'user': recipient}
        count = models.Award.objects.filter(**filters).count()
        self.assertEquals(count, expected_count)

    def assert_accepted_answer_badge_works(self,
                                    badge_key = None,
                                    min_score = None,
                                    expected_count = 1,
                                    previous_count = 0,
                                    trigger = None
                                ):
        assert(trigger in ('accept_best_answer', 'upvote_answer'))
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u2, question = question)
        answer.score = min_score - 1
        answer.save()

        recipient = answer.author

        if trigger == 'accept_best_answer':
            self.u1.upvote(answer)
            self.assert_have_badge(badge_key, recipient, previous_count)
            self.u1.accept_best_answer(answer)
        else:
            self.u1.accept_best_answer(answer)
            self.assert_have_badge(badge_key, recipient, previous_count)
            self.u1.upvote(answer)
        self.assert_have_badge(badge_key, recipient, expected_count)

    def assert_upvoted_answer_badge_works(self, 
                                    badge_key = None,
                                    min_score = None,
                                    multiple = False
                                ):
        """test answer badge where answer author is the recipient
        where badge award is triggered by upvotes
        * min_score - minimum # of upvotes required
        * multiple - multiple award or not
        * badge_key - key on askbot.models.badges.Badge object
        """
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u2, question = question)
        answer.score = min_score - 1
        answer.save()
        self.u1.upvote(answer)
        self.assert_have_badge(badge_key, recipient = self.u2)
        self.u3.upvote(answer)
        self.assert_have_badge(badge_key, recipient = self.u2, expected_count = 1)
        
        #post another question and check that there are no new badges
        answer2 = self.post_answer(user = self.u2, question = question)
        answer2.score = min_score - 1
        answer2.save()
        self.u1.upvote(answer2)

        if multiple == True:
            expected_count = 2
        else:
            expected_count = 1

        self.assert_have_badge(
                badge_key,
                recipient = self.u2,
                expected_count = expected_count
            )

    def assert_upvoted_question_badge_works(self, 
                                    badge_key = None,
                                    min_score = None,
                                    multiple = False
                                ):
        """test question badge where question author is the recipient
        where badge award is triggered by upvotes
        * min_score - minimum # of upvotes required
        * multiple - multiple award or not
        * badge_key - key on askbot.models.badges.Badge object
        """
        question = self.post_question(user = self.u1)
        question.score = min_score - 1
        question.save()
        self.u2.upvote(question)
        self.assert_have_badge(badge_key, recipient = self.u1)
        self.u3.upvote(question)
        self.assert_have_badge(badge_key, recipient = self.u1, expected_count = 1)
        
        #post another question and check that there are no new badges
        question2 = self.post_question(user = self.u1)
        question2.score = min_score - 1
        question2.save()
        self.u2.upvote(question2)

        if multiple == True:
            expected_count = 2
        else:
            expected_count = 1

        self.assert_have_badge(
                        badge_key,
                        recipient = self.u1,
                        expected_count = expected_count
                    )

    def test_disciplined_badge(self):
        question = self.post_question(user = self.u1)
        question.score = settings.DISCIPLINED_BADGE_MIN_UPVOTES
        question.save()
        self.u1.delete_question(question)
        self.assert_have_badge('disciplined', recipient = self.u1)

        question2 = self.post_question(user = self.u1)
        question2.score = settings.DISCIPLINED_BADGE_MIN_UPVOTES
        question2.save()
        self.u1.delete_question(question2)
        self.assert_have_badge('disciplined', recipient = self.u1, expected_count = 2)

    def test_peer_pressure_badge(self):
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u1, question = question)
        answer.score = -1*settings.PEER_PRESSURE_BADGE_MIN_DOWNVOTES
        answer.save()
        self.u1.delete_answer(answer)
        self.assert_have_badge('peer-pressure', recipient = self.u1)

    def test_teacher_badge(self):
        self.assert_upvoted_answer_badge_works(
            badge_key = 'teacher',
            min_score = settings.TEACHER_BADGE_MIN_UPVOTES,
            multiple = False
        )

    def test_nice_answer_badge(self):
        self.assert_upvoted_answer_badge_works(
            badge_key = 'nice-answer',
            min_score = settings.NICE_ANSWER_BADGE_MIN_UPVOTES,
            multiple = True
        )

    def test_nice_question_badge(self):
        self.assert_upvoted_question_badge_works(
            badge_key = 'nice-question',
            min_score = settings.NICE_QUESTION_BADGE_MIN_UPVOTES,
            multiple = True
        )

    def test_popular_question_badge(self):
        question = self.post_question(user = self.u1)
        min_views = settings.POPULAR_QUESTION_BADGE_MIN_VIEWS
        question.view_count = min_views - 1 
        question.save()

        #patch not_a_robot_request to return True
        from askbot.utils import functions
        functions.not_a_robot_request = lambda v: True

        url = question.get_absolute_url()

        self.client.login(method='force', user_id = self.u2.id)
        self.client.get(url)
        self.assert_have_badge('popular-question', recipient = self.u1)

        self.client.login(method='force', user_id = self.u3.id)
        self.client.get(url)
        self.assert_have_badge('popular-question', recipient = self.u1, expected_count = 1)

        question2 = self.post_question(user = self.u1)
        question2.view_count = min_views - 1
        question2.save()
        self.client.login(method='force', user_id = self.u2.id)
        self.client.get(question2.get_absolute_url())
        self.assert_have_badge('popular-question', recipient = self.u1, expected_count = 2)

    def test_student_badge(self):
        question = self.post_question(user = self.u1)
        self.u2.upvote(question)
        self.assert_have_badge('student', recipient = self.u1)
        self.u3.upvote(question)
        self.assert_have_badge('student', recipient = self.u1, expected_count = 1)

        question2 = self.post_question(user = self.u1)
        self.u2.upvote(question)
        self.assert_have_badge('student', recipient = self.u1, expected_count = 1)

    def test_supporter_badge(self):
        question = self.post_question(user = self.u1)
        self.u2.upvote(question)
        self.assert_have_badge('supporter', recipient = self.u2)

        answer = self.post_answer(user = self.u1, question = question)
        self.u3.upvote(answer)
        self.assert_have_badge('supporter', recipient = self.u3)
        self.u2.upvote(answer)
        self.assert_have_badge('supporter', recipient = self.u2, expected_count = 1)

    def test_critic_badge(self):
        question = self.post_question(user = self.u1)
        self.u2.downvote(question)
        self.assert_have_badge('critic', recipient = self.u2)

        answer = self.post_answer(user = self.u1, question = question)
        self.u3.downvote(answer)
        self.assert_have_badge('critic', recipient = self.u3)
        self.u2.downvote(answer)
        self.assert_have_badge('critic', recipient = self.u2, expected_count = 1)

    def test_self_learner_badge(self):
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u1, question = question)
        min_votes = settings.SELF_LEARNER_BADGE_MIN_UPVOTES
        answer.score = min_votes - 1
        answer.save()
        self.u2.upvote(answer)
        self.assert_have_badge('self-learner', recipient = self.u1)

        #copy-paste of the first question, except expect second badge
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u1, question = question)
        answer.score = min_votes - 1
        answer.save()
        self.u2.upvote(answer)
        self.assert_have_badge('self-learner', recipient = self.u1, expected_count = 2)

        question = self.post_question(user = self.u2)
        answer = self.post_answer(user = self.u1, question = question)
        answer.score = min_votes - 1
        answer.save()
        self.u2.upvote(answer)
        #no badge when asker != answerer
        self.assert_have_badge(
            'self-learner',
            recipient = self.u1,
            expected_count = 2
        )

    def test_civic_duty_badge(self):
        settings.update('CIVIC_DUTY_BADGE_MIN_VOTES', 2)
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u2, question = question)
        answer2 = self.post_answer(user = self.u1, question = question)
        self.u3.upvote(question)
        self.u3.downvote(answer)
        self.assert_have_badge('civic-duty', recipient = self.u3)
        self.u3.upvote(answer2)
        self.assert_have_badge('civic-duty', recipient = self.u3, expected_count = 1)
        self.u3.downvote(answer)
        self.assert_have_badge('civic-duty', recipient = self.u3, expected_count = 1)

    def test_scholar_badge(self):
        question = self.post_question(user = self.u1)
        answer = self.post_answer(user = self.u2, question = question)
        self.u1.accept_best_answer(answer)
        self.assert_have_badge('scholar', recipient = self.u1)
        answer2 = self.post_answer(user = self.u2, question = question)
        self.u1.accept_best_answer(answer2)
        self.assert_have_badge(
            'scholar',
            recipient = self.u1,
            expected_count=1
        )

    def assert_enlightened_badge_works(self, trigger):
        self.assert_accepted_answer_badge_works(
            'enlightened',
            min_score = settings.ENLIGHTENED_BADGE_MIN_UPVOTES,
            expected_count = 1,
            trigger = trigger
        )
        self.assert_accepted_answer_badge_works(
            'enlightened',
            min_score = settings.ENLIGHTENED_BADGE_MIN_UPVOTES,
            expected_count = 1,
            previous_count = 1,
            trigger = trigger
        )

    def assert_guru_badge_works(self, trigger):
        self.assert_accepted_answer_badge_works(
            'guru',
            min_score = settings.GURU_BADGE_MIN_UPVOTES,
            expected_count = 1,
            trigger = trigger
        )
        self.assert_accepted_answer_badge_works(
            'guru',
            min_score = settings.GURU_BADGE_MIN_UPVOTES,
            previous_count = 1,
            expected_count = 2,
            trigger = trigger
        )

    def test_enlightened_badge1(self):
        self.assert_enlightened_badge_works('upvote_answer')

    def test_enlightened_badge2(self):
        self.assert_enlightened_badge_works('accept_best_answer')

    def test_guru_badge1(self):
        self.assert_guru_badge_works('upvote_answer')

    def test_guru_badge1(self):
        self.assert_guru_badge_works('accept_best_answer')