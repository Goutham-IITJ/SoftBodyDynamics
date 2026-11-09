"""Predict first, score later; never refits or accepts observation in predict mode."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import datetime
import json
import math
from demo.model import configuration,digest,new_sponge,solve,CONDITION


def predict(mass_g,condition,initial_state,experiment_id):
    if not math.isfinite(mass_g) or mass_g<0:raise ValueError('Use actual measured total bottle mass in grams')
    if condition!=CONDITION:raise ValueError('Frozen model only supports centered, full-face stationary loading')
    if not initial_state.strip() or not experiment_id.strip():raise ValueError('Initial-state notes and experiment ID are required')
    config=configuration();force=mass_g/1000*config['gravity_m_s2']
    state=solve(new_sponge(config),force)
    record=dict(kind='frozen_prediction_before_observation',experiment_id=experiment_id,
                created_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                actual_measured_total_bottle_mass_g=mass_g,force_N=force,loading_condition=condition,
                initial_state_notes=initial_state,frozen_model=config,model_sha256=digest(config),
                predicted_compression_mm=state.displacement*1000,min_J=state.min_J,
                free_residual_N=state.free_residual,reaction_error_N=state.top_reaction-force,
                interpretation='Quasi-static equilibrium only; no recovery timing; no automatic refit')
    record['receipt_sha256']=digest(record)
    return record


def score(receipt,observation):
    original=dict(receipt);checksum=original.pop('receipt_sha256',None)
    if checksum!=digest(original):raise ValueError('Prediction receipt was changed')
    if receipt['kind']!='frozen_prediction_before_observation':raise ValueError('Not a prediction receipt')
    if receipt['model_sha256']!=digest(configuration()):raise ValueError('Current frozen model differs from receipt')
    if observation.get('experiment_id')!=receipt['experiment_id']:raise ValueError('Experiment IDs differ')
    if observation.get('loading_condition')!=receipt['loading_condition']:raise ValueError('Loading conditions differ')
    if not str(observation.get('initial_state_notes','')).strip():raise ValueError('Observed initial-state notes required')
    x=observation.get('observed_settled_compression_mm')
    if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or x<0:
        raise ValueError('Supply actual finite, nonnegative settled compression in mm')
    error=receipt['predicted_compression_mm']-x
    return dict(kind='frozen_prediction_evaluation_no_refit',experiment_id=receipt['experiment_id'],
                prediction_receipt_sha256=checksum,model_sha256=receipt['model_sha256'],
                predicted_compression_mm=receipt['predicted_compression_mm'],observed_compression_mm=x,
                residual_prediction_minus_observation_mm=error,
                illustrative_engineering_allowance_mm=.3+.1*x,
                within_illustrative_allowance=abs(error)<=.3+.1*x,
                observation_within_13mm_search_domain=x<=13,observation=observation,
                warning='Allowance is not a confidence interval or proof of validation; no model parameter changed')


def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('predict');p.add_argument('--mass-g',type=float,required=True)
    p.add_argument('--condition',choices=[CONDITION],required=True);p.add_argument('--initial-state',required=True)
    p.add_argument('--experiment-id',required=True);p.add_argument('--output',type=Path,required=True)
    s=sub.add_parser('score');s.add_argument('--prediction',type=Path,required=True)
    s.add_argument('--observation',type=Path,required=True);s.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; choose a new path to preserve the record')
    try:
        if args.command=='predict':result=predict(args.mass_g,args.condition,args.initial_state,args.experiment_id)
        else:result=score(json.loads(args.prediction.read_text()),json.loads(args.observation.read_text()))
        write_new(args.output,result)
    except (ValueError,RuntimeError) as e:parser.exit(2,f'{e}\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
