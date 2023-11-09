from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/')
def index():
    return "API is running"

@app.route('/message', methods=['POST'])
def respond_message():
    try:
        # Log the received request
        print("Received request:", request.json)

        messages = request.json.get('messages') 
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Messages content missing or not a list"}), 400

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.4,
            max_tokens=1000
        )

        # Log the complete OpenAI response
        print("OpenAI response:", response)

        if not hasattr(response, 'choices'):
            return jsonify({"error": "Invalid response from OpenAI"}), 500

        chat_response = response.choices[0].message['content'].strip()
        return jsonify({'response': chat_response})

    except Exception as e:
        print(f"Error during API call to OpenAI: {e}")
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
