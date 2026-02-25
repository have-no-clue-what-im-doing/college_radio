import yaml

services = {}

for i in range(1, 24):
    services[f'college_stream_{i}'] = {
        'container_name': f'college-radio-{i}',
        'hostname': f'college-radio-{i}',
        'build': '.',
        'environment': {'GROUP': i},
        'logging': {
            'driver': 'loki',
            'options': {
                'loki-url': 'http://10.10.13.17:3100/loki/api/v1/push',
                'loki-batch-size': '500',
                'loki-timeout': '10s',
                'loki-retries': '2',
                'labels': 'app=collage_radio'
            }
        },
        'restart': 'unless-stopped'
    }

with open('docker-compose.yaml', 'w') as f:
    yaml.dump({'services': services}, f, default_flow_style=False, sort_keys=False)