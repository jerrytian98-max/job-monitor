import os
import subprocess
import yaml

def run_command(cmd):
    print(f"执行命令: {cmd}")
    subprocess.run(cmd, shell=True)

# 1. 更新 config.yaml
config_path = "config.yaml"
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 更新邮箱授权码
    if 'email' in config:
        config['email']['auth_code'] = 'JVfNdNW2ESqGXi5x'
    
    # 更新 API Key
    config['gemini_api_key'] = 'sk-api-2Ion4WQ5BiRpyscB5nmsrd3Ie0Ntny6ImgqqJ6_BBYOg1FeoykwHL7RJuuxRL99b4YFyvVHVt3KifC-tAjECN4eGNL34b4xzgFmnC-bJAa71DDvHmo7LIjA'
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)
    print("成功更新 config.yaml 文件！")
except Exception as e:
    print(f"更新配置文件失败: {e}")

# 2. 提交到 Git 并推送到 GitHub
run_command("git pull --rebase origin main")
run_command("git add config.yaml")
run_command('git commit -m "Update API key and email auth code"')
run_command("git push origin main")

print("\n==== 配置更新并推送完成！====")
print("请现在去 GitHub 网页的 Actions 重新运行一次 Workflow 试试看！")