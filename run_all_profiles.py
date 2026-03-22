import os
import glob
import subprocess
import sys

def run_profile(profile_name):
    print(f"\n{'='*50}\n🚀 正在运行分身: {profile_name if profile_name else '默认(default)'}\n{'='*50}")
    env = os.environ.copy()
    if profile_name:
        env['JOB_PROFILE'] = profile_name
    else:
        if 'JOB_PROFILE' in env:
            del env['JOB_PROFILE']
            
    subprocess.run([sys.executable, "-c", "from app import run_monitor; run_monitor()"], env=env)

if __name__ == '__main__':
    # 查找所有的配置文件
    configs = glob.glob('config*.yaml')
    
    if not configs:
        print("没有找到任何配置文件(config*.yaml)")
        sys.exit(1)
        
    for c in configs:
        # config.yaml -> ''
        # config_user2.yaml -> 'user2'
        name = c.replace('config', '').replace('.yaml', '')
        if name.startswith('_'):
            name = name[1:]
        run_profile(name)
