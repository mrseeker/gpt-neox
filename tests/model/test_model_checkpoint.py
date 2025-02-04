"""
instantiate models, save checkpoints, load checkpoints, compare loaded parameters to saved parameters and compare forward pass outputs

This tests contain a relatively large number of functions. They are not split into separate tests because a lot of boilerplate (e.g. instantiate model) needs
to run in order to perform follow up tests. Joining in one test reduces runtime at the expense of decreased transparency of test results in case of failures.
"""
if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.abspath(''))

import pytest
from tests.common import distributed_test, clear_test_dirs, model_setup, binary, parametrize
import torch

PARAMS_TO_TEST = {
    "pipe_parallel_size,model_parallel_size": [[0, 1], [1, 2], [0, 2], [2, 1]],
    "checkpoint_validation_with_forward_pass": [True]
}

parameters, names = parametrize(PARAMS_TO_TEST, max_tests=50, seed=None)
@pytest.mark.parametrize("param_dict", parameters, ids=names)
def test_train(param_dict):
    @distributed_test(world_size=2)
    def wrapper():
        run_checkpoint_test(param_dict=param_dict)
    wrapper()


def run_checkpoint_test(yaml_list=None, param_dict=None):
    
    from megatron.checkpointing import load_checkpoint
    from megatron.checkpointing import save_checkpoint

    model, optimizer, lr_scheduler, args_loaded = model_setup(yaml_list, param_dict, clear_data=True)

    # save model checkpoint
    save_checkpoint(neox_args=args_loaded, iteration=42, model=model, optimizer=optimizer, lr_scheduler=lr_scheduler)


    # reload model from checkpoint
    reloaded_model, reloaded_optimizer, reloaded_lr_scheduler, args_reloaded = model_setup(yaml_list, param_dict, clear_data=False)
    iteration = load_checkpoint(neox_args=args_reloaded, model=reloaded_model, optimizer=reloaded_optimizer, lr_scheduler=reloaded_lr_scheduler)

    #ensure same checkpoint is loaded
    assert iteration == 42, "run_checkpoint_test() iteration loaded from checkpoint correct"

    #check all weight groups are the same
    for idx, ((n1, p1), (n2, p2)) in enumerate(zip(list(model.module.named_parameters()), list(reloaded_model.module.named_parameters()))):
        assert n1 == n2
        params_equal = (p1 == p2).all().item()
        assert params_equal, "run_checkpoint_test() params equal: "+str(n1)

    if torch.distributed.get_world_size() == 1 or torch.distributed.get_rank() == 0:
        clear_test_dirs()

if __name__ == "__main__":
    params = list(parametrize(PARAMS_TO_TEST, max_tests=50, seed=None))
    test_train(params[0])