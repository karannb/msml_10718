"""Offline regression checks; no Anthropic dependency or network needed."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eval_google as g


class FakeClient:
    def __init__(self, verdict, stop='end_turn'):
        self.calls = 0
        self.verdict = verdict
        self.stop = stop
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(stop_reason=self.stop,
            content=[SimpleNamespace(type='text', text=json.dumps(self.verdict))],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50))


class GoogleEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.job = next(g.jobs(0, 1, ['quality']))
        self.quality = {axis: {'score': 4, 'reason': 'Test fixture.'} for axis in g.AXES}
        self.quality.update(diagnosis_matches_reference='yes', generic_phrases=[])

    def test_all_inputs_and_frozen_passages(self):
        self.assertEqual(g.validate_inputs()['source_positions'], 960)

    def test_prompt_uses_exact_answer_and_no_assistant_grade(self):
        selected = g.read(g.INPUT / 'selections/000.json')
        self.assertIn(selected['advice'], self.job['prompt'])
        self.assertNotIn('Reference-only audit', self.job['prompt'])
        audited = next(g.jobs(0, 1, ['quality'], 'audited'))
        self.assertIn('Reference-only audit', audited['prompt'])
        self.assertNotIn('assistant_in_conversation', self.job['prompt'])
        retrieval = list(g.jobs(17, 18, ['retrieval']))
        self.assertEqual(len(retrieval), 4)
        self.assertNotIn(1, [j['rank'] for j in retrieval])

    def test_resume_and_stale_cache_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'grade.json'; client = FakeClient(self.quality)
            g.grade_job(client, 'fixture-model', self.job, dest)
            g.grade_job(client, 'fixture-model', self.job, dest)
            self.assertEqual(client.calls, 1)
            changed = dict(self.job, prompt=self.job['prompt'] + ' changed')
            with self.assertRaisesRegex(ValueError, 'Stale cache'):
                g.grade_job(client, 'fixture-model', changed, dest)
            self.assertEqual(client.calls, 1)

    def test_invalid_or_truncated_response_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'grade.json'
            bad = copy.deepcopy(self.quality); bad['harmfulness']['score'] = 6
            with self.assertRaisesRegex(ValueError, 'outside'):
                g.grade_job(FakeClient(bad), 'fixture-model', self.job, dest)
            self.assertFalse(dest.exists())
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                g.grade_job(FakeClient(self.quality, 'max_tokens'), 'fixture-model', self.job, dest)
            self.assertFalse(dest.exists())

    def test_retrieval_hit_requires_valid_source_passage(self):
        job = next(g.jobs(0, 1, ['retrieval']))
        verdict = dict(action_hit='hit', reason='Fixture.', supporting_spans=[])
        with self.assertRaisesRegex(ValueError, 'without evidence'):
            g.validate_verdict(verdict, job['schema'], job)
        verdict['supporting_spans'] = [dict(file='../references.jsonl', start_line=1, end_line=1)]
        with self.assertRaisesRegex(ValueError, 'outside source'):
            g.validate_verdict(verdict, job['schema'], job)

    def test_capacity_boundary_and_partial_report(self):
        resolved = dict(advice='yes', harmful=False, actions=[dict(minutes=15, per_day=1, cost_usd=0, unclear=False)])
        self.assertFalse(g.derive(resolved, self.quality)['solved'])
        resolved['actions'][0]['minutes'] = 14
        self.assertTrue(g.derive(resolved, self.quality)['solved'])
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            g.save(run / 'run.json', dict(model='fixture-model', reference_mode='dataset'))
            g.grade_job(FakeClient(self.quality), 'fixture-model', self.job, run / 'grades/000-quality.json')
            summary = g.report(run)
            self.assertIsNone(summary['groups']['title_paraphrase']['verified_hit_rate'])
            rows = g.jsonl(run / 'evaluation-results.jsonl')
            self.assertEqual(len(rows), 192)
            self.assertIsNone(rows[0]['action_hit'])
            self.assertIsNone(rows[0]['solved'])
            self.assertEqual(rows[0]['completed_calls'], 1)


if __name__ == '__main__':
    unittest.main()
