import yaml

with open('./config.yaml', 'r') as file:
    yaml_config = yaml.safe_load(file)




college_dict = yaml_config['college_dict']
database_dict = yaml_config['database']
spotify_dict = yaml_config['spotify']
print(yaml_config)