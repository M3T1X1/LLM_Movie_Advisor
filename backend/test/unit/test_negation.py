from django.test import SimpleTestCase
from backend.recommendation_agents.profiling import ProfilingAgent, ProfilingAgentInput


class NegationTests(SimpleTestCase):
    def ground(self, text, history=()):
        return ProfilingAgent._ground_output(ProfilingAgentInput(text, history), ProfilingAgent._fallback_output(text))

    def test_negative_genres(self):
        for text, positive, negative in (
            ('Komedia, ale nie animacja. Film do 90 minut.', ('Komedia',), ('Animacja',)),
            ('Poleć film, nie horror ani thriller. Wolę komedię.', ('Komedia',), ('Horror','Thriller')),
            ('Nie chcę horroru, ale komedia może być.', ('Komedia',), ('Horror',)),
            ('Nie animacja, tylko komedia.', ('Komedia',), ('Animacja',)),
            ('Nie horror, wolę komedię.', ('Komedia',), ('Horror',)),
            ('Recommend comedy but not animation.', ('Komedia',), ('Animacja',)),
            ('Poleć film bez dramatu i romansu, ale komedię.', ('Komedia',), ('Dramat','Romans')),
        ):
            with self.subTest(text=text):
                result=self.ground(text)
                self.assertEqual(result.genres, positive)
                for value in negative:self.assertIn(value,result.avoid)

    def test_not_only_is_not_exclusion(self):
        result=self.ground('Poleć film, nie tylko komedię, ale też horror.')
        self.assertIn('Komedia',result.genres)
        self.assertNotIn('Komedia',result.avoid)

    def test_negative_space_is_not_positive_theme(self):
        for text in ('Poleć SF, ale nie o kosmosie ani astronautach.',
                     'Recommend science fiction but not about space.'):
            result=self.ground(text)
            self.assertNotIn('podróż kosmiczna',result.themes)
            self.assertIn('podróż kosmiczna',result.excluded_themes)

    def test_negative_follow_up_removes_inherited_theme(self):
        result=self.ground('Tym razem nie o kosmosie.', (
            {'role':'user','content':'Poleć film science fiction o kosmosie.'},))
        self.assertNotIn('podróż kosmiczna',result.themes)
        self.assertIn('podróż kosmiczna',result.excluded_themes)
        self.assertEqual(result.intent, 'recommendation')

    def test_denial_of_movie_scope(self):
        self.assertEqual(self.ground('Nie pytam o filmy. Chcę przepis na naleśniki.').intent,'other')

    def test_off_topic_does_not_inherit_negative_theme_as_intent(self):
        result = self.ground('A teraz podaj przepis na naleśniki.', (
            {'role': 'user', 'content': 'Poleć SF o kosmosie.'},
            {'role': 'user', 'content': 'Tym razem nie o kosmosie.'},
        ))
        self.assertEqual(result.intent, 'other')
