from flask import Flask, request, jsonify
import requests
import os
import base64
import logging
import re
import json
from git import Repo
import shutil
import git
import subprocess
import textwrap
import threading

git.refresh(path='/usr/bin/git')



logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

with open('config.json') as f:
    config = json.load(f)

AZURE_PAT = os.environ['PAT_AZURE']
API_ENDPOINT = config['api_endpoint']
ORGANIZATION_NAME = config['organization_name']

if isinstance(AZURE_PAT, bytes):
    AZURE_PAT = AZURE_PAT.decode('utf-8')

encoded_pat = base64.b64encode(f':{AZURE_PAT}'.encode('utf-8')).decode('utf-8')
headers = {
    'Authorization': f'Basic {encoded_pat}',
    'Content-Type': 'application/json',
}

def clone_repository(clone_url, repository_name):
    # Use uma expressão regular para substituir qualquer coisa entre 'https://' e '@dev.azure.com' pelo AZURE_PAT
    auth_clone_url = re.sub(r'https://.*?@', f'https://{AZURE_PAT}@', clone_url)
    repo_dir = f'/app/repo/{repository_name}'
    if not os.path.exists(repo_dir):
        command = f'git clone {auth_clone_url} {repo_dir}'
        process = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        if process.returncode != 0:
            logging.error(f'Failed to clone repository: {process.stderr}')
            raise Exception(f'Failed to clone repository: {process.stderr}')
    return repo_dir


def update_repository(repo_dir):
    repo = git.Repo(repo_dir)
    repo.git.fetch('origin')

def get_diff(repo_dir, source_commit_id, target_commit_id):
    repo = git.Repo(repo_dir)
    diff_output = repo.git.diff(f'{target_commit_id}..{source_commit_id}')
    return diff_output

def validate_pr_data(pr_data):
    try:
        organization = ORGANIZATION_NAME  # Use o nome da organização do config.json
        project_url = pr_data['resource']['repository']['project']['url']
        project = pr_data['resource']['repository']['project']['name']
        repositoryId = pr_data['resource']['repository']['id']
        pullRequestId = pr_data['resource']['pullRequestId']
    except KeyError as e:
        logging.error(f'KeyError: {e}')
        raise ValueError(f'Missing necessary information from the webhook payload: {str(e)}')
    except AttributeError:
        logging.error('Failed to extract organization name from project URL')
        raise ValueError('Missing necessary information from the webhook payload: organization name')
    return organization, project, repositoryId, pullRequestId


@app.route('/webhook', methods=['POST'])
def webhook():
    response = jsonify({'status': 'received'}), 200
    threading.Thread(target=process_webhook, args=(request.json,)).start()
    return response
    
def process_webhook(pr_data):
    with app.app_context():
        if pr_data is None:
            logging.error('Payload não é um JSON válido ou cabeçalho Content-Type incorreto.')
            return jsonify({'error': 'Bad Request'}), 400  
        logging.debug(f'Payload recebido: {pr_data}')
        try:
            response = analyze_code_and_comment(pr_data)
            if response:
                return response  
            return jsonify({'status': 'success'}), 200  
        except Exception as e:
            logging.exception("Erro ao processar o webhook")
            return jsonify({'error': f"Top-level error: {str(e)}"}), 400  


    
def save_diff_to_file(diff_content):
    file_path = '/app/diff.txt'
    with open(file_path, 'w') as file:
        file.write(diff_content)
    return file_path

def analyze_code_and_comment(pr_data):
    try:
        organization, project, repositoryId, pullRequestId = validate_pr_data(pr_data)
        clone_url = pr_data['resource']['repository']['remoteUrl']
        repository_name = pr_data['resource']['repository']['name']
        repo_dir = clone_repository(clone_url, repository_name)
        update_repository(repo_dir)

        source_commit_id = pr_data['resource']['lastMergeSourceCommit']['commitId']
        target_commit_id = pr_data['resource']['lastMergeTargetCommit']['commitId']
        diff_content = get_diff(repo_dir, source_commit_id, target_commit_id)
        
        diff_file_path = save_diff_to_file(diff_content)
        
        logging.debug(f'organization: {organization}, project: {project}, repositoryId: {repositoryId}, pullRequestId: {pullRequestId}')
        if not all([organization, project, repositoryId, pullRequestId]):
            raise ValueError('Missing necessary information from the webhook payload')

        context = textwrap.dedent("""
            Você é um líder técnico revisando uma alteração proposta no código. Por favor, considere os seguintes pontos durante a análise:
            - Clean Code: O código é legível, bem organizado e possui nomes de variáveis e funções descritivos?
            - DRY (Don't Repeat Yourself): Existem partes do código que são repetidas e que poderiam ser refatoradas?
            - Princípios SOLID: O código adere aos princípios SOLID? Por exemplo, ele segue o princípio da responsabilidade única?
            - Segurança: Existem potenciais falhas de segurança, como vazamento de dados sensíveis ou vulnerabilidades de injeção de SQL?
            - Exemplo: Se possível, forneça exemplos de como o código poderia ser refatorado para melhor aderir a estas práticas.

            Identifique e comente sobre qualquer problema encontrado, sugerindo melhorias específicas que podem ser feitas para abordar cada problema.
        """)

        
        full_content = context + "`\n" + diff_content + "`"
        
        messages = [
            {"role": "user", "content": full_content}
        ]
        review_response = requests.post(API_ENDPOINT, json={'messages': messages}).json()

        if 'response' not in review_response:
            return jsonify({'error': 'Unexpected API response'}), 500
        
        review = review_response['response']

        comments_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repositoryId}/pullRequests/{pullRequestId}/threads?api-version=6.0"
        comment_data = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": review,
                    "commentType": 1
                }
            ]
        }
        logging.debug(f'Diff saved to: {diff_file_path}')
        
        comment_response = requests.post(comments_url, headers=headers, json=comment_data)
        if comment_response.status_code != 200:
            raise Exception(f"Failed to post comment: {comment_response.text}")

    except Exception as e:
        logging.exception(f'Erro na função analyze_code_and_comment: {str(e)}')
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001) 
