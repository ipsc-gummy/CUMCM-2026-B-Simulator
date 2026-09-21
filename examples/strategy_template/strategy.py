"""Minimal upload-format example. Replace the body with your strategy."""


def run(api):
    # This small call sequence checks the public evaluator contract only.
    # It is intentionally not presented as a competitive strategy.
    api.switch_channel(1)
    api.move((0.0, 0.0))
    observation = api.measure()
    if observation.get('measure_result') == 'near':
        api.clear()
