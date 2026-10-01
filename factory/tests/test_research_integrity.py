"""Counterexamples for the KLStream local factory repair. All inputs are fixtures."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import gatekeeper as g
from engine.io import read_json,write_json,inventory,sha,digest,EvidenceError
from engine.supervisor import (init_supervisor_keys,sign_receipt,verify_receipt_signature,
                               execution_binding,SCHEME_HMAC_SHA256)
from engine.contract import command_to_contract,resolve_contract,validate_contract
from engine.metrics import binary_metrics,paired_inference,quantile
from tests.test_v3 import fixture,evaluate


class IntegrityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.keys=patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(self.base/'keys/supervisor.key')})
        self.keys.start();self.root=self.base/'workspace';self.root.mkdir();self.plan=fixture(self.root)
        self.quiet=contextlib.redirect_stdout(io.StringIO());self.quiet.__enter__()
    def tearDown(self):
        self.quiet.__exit__(None,None,None);self.keys.stop();self.tmp.cleanup()
    def execute(self):
        g.freeze(self.root);self.assertEqual(g.run_exp(self.root,'known'),0)
        self.execution=g.active(self.root)[1]/'runs/known/attempt0001/execution.json'
        self.assertEqual(evaluate(self.root)['errors'],[])
    def alter(self,fn):
        record=read_json(self.execution);fn(record);write_json(self.execution,record)
        self.assertTrue(evaluate(self.root)['errors'])
    def test_missing_signature_blocks_full_audit(self):
        self.execute();self.alter(lambda r:r.pop('supervisor_receipt'))
    def test_invalid_signature_blocks_full_audit(self):
        self.execute();self.alter(lambda r:r['supervisor_receipt'].update(supervisor_signature='AAAA'))
    def test_receipt_project_identity_checked_even_when_resigned(self):
        self.execute()
        def mutate(r):
            r['supervisor_receipt']['project_id']='other'
            r['supervisor_receipt']=sign_receipt(r['supervisor_receipt'])
        self.alter(mutate)
    def test_unsigned_nonce_mutation_blocks_full_audit(self):
        self.execute();self.alter(lambda r:r.update(run_nonce='changed'))
    def test_unsigned_runtime_mutation_blocks_full_audit(self):
        self.execute();self.alter(lambda r:r['runtime_attestation'].update(platform_machine='invented'))
    def test_output_rehash_cannot_bypass_authentication(self):
        self.execute();a=self.execution.parent
        (a/'result.json').write_text('{}')
        outputs=inventory(self.root,[g.relpath(a,self.root)],reject_dangerous_ext=False)
        outputs.pop(g.relpath(self.execution,self.root))
        self.alter(lambda r:r.update(outputs=outputs))
    def test_missing_freeze_signature_blocks_audit(self):
        self.execute();path=g.active(self.root)[1]/'freeze.json';f=read_json(path)
        f.pop('freeze_attestation');write_json(path,f);self.assertTrue(evaluate(self.root)['errors'])
    def test_rehashed_freeze_without_new_signature_blocks_audit(self):
        self.execute();path=g.active(self.root)[1]/'freeze.json';f=read_json(path)
        f['snapshot_merkle_root']='0'*64;write_json(path,f);self.assertTrue(evaluate(self.root)['errors'])
    def test_unmeasured_resources_are_null(self):
        self.execute();r=read_json(self.execution);resources=r['supervisor_receipt']['resource_observations']
        self.assertIsNone(resources['cpu_time_seconds']);self.assertIsNone(resources['memory_peak_bytes'])
        self.assertEqual(resources['wall_time_seconds'],r['duration_sec'])
    def test_result_path_cannot_promote_assurance(self):
        self.assertEqual(g._compute_assurance_level({'computed_runs':{'x':{'result_path':'result.json'}},'checks_executed':['RUN']}),'STRUCTURALLY_VALIDATED')
    def test_verified_run_has_only_local_assurance(self):
        self.execute();out=evaluate(self.root)
        self.assertEqual(g._compute_assurance_level(out),'SUPERVISOR_ATTESTED')
        self.assertEqual(g._assurance_with_review('SUPERVISOR_ATTESTED',{'review_mode':'same_session_self_review'}),'SUPERVISOR_ATTESTED')
    def test_verification_never_creates_missing_keys(self):
        init_supervisor_keys();r=sign_receipt({'x':1});pub=Path(os.environ['FACTORY_SUPERVISOR_KEY']).with_suffix('.pub');pub.unlink()
        with self.assertRaises(EvidenceError):verify_receipt_signature(r)
        self.assertFalse(pub.exists())
    def test_partial_key_loss_never_rotates_existing_private_key(self):
        priv,pub,_=init_supervisor_keys();before=priv.read_bytes();pub.unlink()
        with self.assertRaises(EvidenceError):init_supervisor_keys()
        self.assertEqual(priv.read_bytes(),before);self.assertFalse(pub.exists())
    def test_hmac_secret_files_are_private_and_scheme_is_bound(self):
        with patch('engine.supervisor._try_ed25519',return_value=False):
            priv,pub,scheme=init_supervisor_keys();self.assertEqual(scheme,SCHEME_HMAC_SHA256)
            self.assertEqual(priv.stat().st_mode&0o777,0o600);self.assertEqual(pub.stat().st_mode&0o777,0o600)
            r=sign_receipt({'x':1});self.assertTrue(verify_receipt_signature(r));r['signature_scheme']='ed25519'
            with self.assertRaises(EvidenceError):verify_receipt_signature(r)
    def test_worker_environment_omits_signing_key_and_unrelated_secrets(self):
        with patch.dict(os.environ,{'UNRELATED_API_TOKEN':'fixture-only'}):
            env=g.execution_env(1);self.assertNotIn('FACTORY_SUPERVISOR_KEY',env);self.assertNotIn('UNRELATED_API_TOKEN',env)
    def test_typed_launch_runs_and_audits_in_same_argument_order(self):
        e=self.plan['experiments'][0];e.pop('command')
        e['execution_contract']={'runtime_id':'python-cpu-v1','entrypoint':'source/run.py',
            'arguments':['supervisor_bound','plan_seed','plan_id'],'network':'allowed'}
        write_json(self.root/g.ROOT_PLAN,self.plan);self.execute()
    def test_legacy_conversion_preserves_literals_and_order(self):
        contract,_=command_to_contract(['python3','source/run.py','literal','{run_dir}','--seed={seed}','{experiment_id}'],['source/run.py'])
        argv,_,_=resolve_contract(contract,self.root,7,'case')
        self.assertEqual(argv[-4:],['literal',str(self.root.resolve()),'--seed=7','case'])
    def test_unenforced_network_policy_rejected(self):
        c={'runtime_id':'python-cpu-v1','entrypoint':'source/run.py','network':'disabled'}
        with self.assertRaises(EvidenceError):validate_contract(c,self.root,['source/run.py'])
    def test_unenforced_memory_policy_rejected(self):
        c={'runtime_id':'python-cpu-v1','entrypoint':'source/run.py','memory_bytes':1024}
        with self.assertRaises(EvidenceError):validate_contract(c,self.root,['source/run.py'])
    def test_output_binary_and_bytecode_files_are_hashed(self):
        p=self.root/'output';(p/'__pycache__').mkdir(parents=True)
        (p/'plugin.so').write_bytes(b'fixture');(p/'__pycache__/x.pyc').write_bytes(b'fixture')
        files=inventory(self.root,['output'],reject_dangerous_ext=False)
        self.assertEqual(set(files),{'output/plugin.so','output/__pycache__/x.pyc'})
    def test_ranking_scores_do_not_get_calibration_metrics(self):
        metrics=binary_metrics([0,1],[-2,3],0,score_kind='ranking')
        self.assertEqual(metrics['auroc'],1);self.assertNotIn('brier',metrics);self.assertNotIn('log_loss',metrics)
    def test_sign_flip_p_value_is_invariant_to_units(self):
        original=paired_inference([1]*5,[0]*5)
        small=paired_inference([1e-20]*5,[0]*5)
        self.assertEqual(original['p_raw'],small['p_raw']);self.assertEqual(small['p_raw'],2/32)
    def test_standardized_effect_and_variance_survive_small_units(self):
        value=paired_inference([1e-200,2e-200,3e-200],[0,0,0])
        self.assertAlmostEqual(value['paired_dz'],2)
        self.assertFalse(value['degenerate_variance'])
    def test_quantile_interpolation_between_finite_extremes(self):
        self.assertEqual(quantile([-1e308,1e308],.5),0)
    def test_flat_sensitivity_is_valid_negative_result(self):
        path=self.base/'flat.json';write_json(path,{'sweeps':[{'parameter':'batch','values':[.5,.5,.5]}]})
        self.assertEqual(g.verify_sensitivity_analysis(path),0)
    def test_f1_has_no_universal_half_chance_level(self):
        self.assertEqual(g._result_findings({'metric':'f1','value':.2,'verdict':'SUPPORTED'}),[])
    def test_negative_verdicts_do_not_count_as_all_supported(self):
        entries=[{'verdict':'NOT_SUPPORTED'}]*3
        self.assertFalse(any(kind=='all_supported' for kind,_ in g._result_findings(entries)))
    def test_zero_observed_failures_need_coverage_not_invented_categories(self):
        path=self.base/'failure.json';write_json(path,{'failures':[],'coverage_statement':'No observed failures in this declared fixture scope.'})
        self.assertEqual(g.verify_failure_taxonomy(path),0)
    def test_invalid_failure_fraction_rejected(self):
        path=self.base/'failure.json';write_json(path,{'failures':[{'category':'case','candidate_ids':['s1'],'prevalence':-1,'severity':'SEV-1'}]})
        self.assertNotEqual(g.verify_failure_taxonomy(path),0)
    def test_empty_contract_cannot_pass_vacuously(self):
        path=self.base/'empty.json';write_json(path,{'checks':[]});self.assertNotEqual(g.check_contract(path),0)
    def test_training_budget_needs_method_specific_rationale(self):
        path=self.base/'training.json';write_json(path,{'epochs_trained':100})
        self.assertNotEqual(g.verify_training_sufficiency(path),0)

    def test_importable_cache_bytecode_cannot_escape_frozen_inventory(self):
        directory=self.root/'source/__pycache__';directory.mkdir()
        (directory/'hidden.pyc').write_bytes(b'fixture')
        with self.assertRaises(EvidenceError):g.freeze(self.root)
    def test_source_directory_code_path_is_expanded_for_review(self):
        self.plan['experiments'][0]['code_paths']=['source']
        write_json(self.root/g.ROOT_PLAN,self.plan);self.execute()
    def test_non_finite_nested_p_value_rejected(self):
        self.assertNotEqual(g.verify_result_plausibility({'nested':{'p_value':float('nan')}}),0)
    def test_plan_numeric_strings_do_not_silently_coerce(self):
        self.plan['experiments'][0]['threshold']='0.5';write_json(self.root/g.ROOT_PLAN,self.plan)
        with self.assertRaises(EvidenceError):g.freeze(self.root)
    def test_deleted_attempt_cannot_be_silently_rerun(self):
        self.execute()
        import shutil
        shutil.rmtree(self.execution.parent)
        with self.assertRaises(EvidenceError):g.run_exp(self.root,'known')
    def test_failed_attempt_requires_disclosed_amendment(self):
        (self.root/'source/run.py').write_text('raise RuntimeError("fixture failure")')
        g.freeze(self.root);self.assertNotEqual(g.run_exp(self.root,'known'),0)
        with self.assertRaises(EvidenceError):g.run_exp(self.root,'known')
    def test_missing_attempt_ledger_blocks_audit(self):
        self.execute();(self.execution.parent.parent/'attempt_ledger.json').unlink()
        self.assertTrue(evaluate(self.root)['errors'])
    def hardware_fixture(self):
        from engine.audit import Audit
        a=Audit(self.root,self.plan,self.root,{},'fixture-engine')
        a.computed={'known':{'result_path':'project/result.json'}}
        a.reports={'known':{'hardware_trials':'trials.csv'}}
        self.plan['hardware']={'experiment_id':'known','min_trials':5,'minimum_sustained_seconds':30}
        text='phase,warmup,duration_sec,samples,batch_size,start_elapsed_sec,end_elapsed_sec\n'
        text+='inference,1,1,1,1,0,1\n'
        for i in range(5):text+=f'inference,0,2,1,1,{10+i*10},{12+i*10}\n'
        path=self.root/'project/trials.csv';path.write_text(text)
        return a,path
    def test_service_rate_and_completion_horizon_have_distinct_denominators(self):
        a,_=self.hardware_fixture();a.hardware();m=a.hardware_results
        self.assertEqual(m['aggregate_service_rate_samples_sec'],.5)
        self.assertEqual(m['observed_completion_rate_samples_sec'],5/42)
        self.assertEqual(m['observed_inference_horizon_sec'],42)
    def test_unknown_warmup_cannot_hide_observations(self):
        a,path=self.hardware_fixture();path.write_text(path.read_text().replace('inference,0','inference,2',1))
        with self.assertRaises(EvidenceError):a.hardware()
    def test_run_duration_cannot_masquerade_as_single_point_latency(self):
        a,path=self.hardware_fixture();path.write_text(path.read_text().replace('inference,0,2,1,1','inference,0,2,5,1',1))
        with self.assertRaises(EvidenceError):a.hardware()
    def test_training_at_budget_cap_is_reported_even_without_convergence(self):
        from engine.audit import Audit
        a=Audit(self.root,self.plan,self.root,{},'fixture-engine');e=self.plan['experiments'][0]
        e['training']={'mode':'fixed','min_epochs':2,'max_epochs':4,'tail_window':2,'relative_tolerance':.01}
        attempt=self.root/'training';attempt.mkdir()
        (attempt/'history.csv').write_text('epoch,train_loss,validation_loss\n1,1,1\n2,.8,1\n3,.6,.5\n4,.4,.5\n')
        (attempt/'initial.bin').write_bytes(b'initial fixture');(attempt/'model.bin').write_bytes(b'final fixture')
        result={'history':'history.csv','epochs_trained':4,'checkpoint_epoch':3,'checkpoint':'model.bin','initial_checkpoint':'initial.bin'}
        a.training(e,result,attempt)
        self.assertTrue(any(d['code']=='NONCONVERGED_AT_REGISTERED_BUDGET' for d in a.diagnostics))
        e['training']['claim_convergence']=True
        with self.assertRaises(EvidenceError):a.training(e,result,attempt)
    def training_history_fixture(self,losses,mode):
        from engine.audit import Audit
        a=Audit(self.root,self.plan,self.root,{},'fixture-engine');e=self.plan['experiments'][0]
        e['training']={'mode':mode,'min_epochs':2,'max_epochs':4,'tail_window':2,
                      'relative_tolerance':.01,'patience':2,'min_delta':0}
        attempt=self.root/'training';attempt.mkdir()
        (attempt/'history.csv').write_text('epoch,train_loss,validation_loss\n'+
                 ''.join(f'{i},{v},{v}\n' for i,v in enumerate(losses,1)))
        (attempt/'initial.bin').write_bytes(b'initial fixture');(attempt/'model.bin').write_bytes(b'final fixture')
        result={'history':'history.csv','epochs_trained':len(losses),'checkpoint_epoch':len(losses),
                'checkpoint':'model.bin','initial_checkpoint':'initial.bin'}
        return a,e,result,attempt
    def test_signed_minimization_losses_are_valid(self):
        a,e,result,attempt=self.training_history_fixture([-1,-2,-3,-4],'fixed')
        a.training(e,result,attempt)
        self.assertTrue(any(d['code']=='NONCONVERGED_AT_REGISTERED_BUDGET' for d in a.diagnostics))
    def test_early_stopping_cap_retains_result_without_convergence_claim(self):
        a,e,result,attempt=self.training_history_fixture([1,.8,.6,.4],'early_stopping')
        a.training(e,result,attempt)
        self.assertTrue(any(d['code']=='EARLY_STOPPING_BUDGET_CAP' for d in a.diagnostics))
        e['training']['claim_convergence']=True
        with self.assertRaises(EvidenceError):a.training(e,result,attempt)
    def test_short_execution_cannot_claim_budget_cap(self):
        a,e,result,attempt=self.training_history_fixture([1,.8,.6],'early_stopping')
        with self.assertRaises(EvidenceError):a.training(e,result,attempt)

if __name__=='__main__':unittest.main()
