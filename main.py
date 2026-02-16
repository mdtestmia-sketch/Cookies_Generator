from flask import Flask, request, jsonify
import instaloader
import pyotp
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)

# ইউজার এজেন্ট কনফিগারেশন
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'


def process_single_account(acc):
    user = acc.get('u')
    pw = acc.get('p')
    key = acc.get('key', "").replace(" ", "")

    L = instaloader.Instaloader(quiet=True)
    L.context._session.headers.update({'User-Agent': UA})

    try:
        # লগইন চেষ্টা
        L.login(user, pw)
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        try:
            # ২এফএ হ্যান্ডলিং
            totp = pyotp.TOTP(key)
            L.two_factor_login(totp.now())
        except:
            return {"user": user, "status": "failed", "reason": "2FA_Error"}
    except Exception as e:
        return {"user": user, "status": "failed", "reason": str(e)}

    # কুকিজ ডিকশনারি থেকে স্ট্রিং বানানো (আপনার দেওয়া ফরম্যাট অনুযায়ী)
    cookies = L.context._session.cookies.get_dict()
    ck_str = "; ".join([f"{key}={val}" for key, val in cookies.items()])

    # ফরম্যাট: User|Pass|Cookies
    # আমরা এই পুরো স্ট্রিংটিই 'result' হিসেবে রিটার্ন করবো
    formatted_result = f"{user}|{pw}|{ck_str}"

    return {
        "user": user,
        "status": "success",
        "cookies": formatted_result
    }


@app.route('/process', methods=['POST'])
def handle_request():
    data = request.json
    if not data or 'accounts' not in data:
        return jsonify({"status": "error", "message": "No data found"}), 400

    accounts = data['accounts']
    success_list = []
    failed_list = []

    # মাল্টিপল একাউন্ট প্রসেস করা (একসাথে ৫টি করে)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_single_account, accounts))

    for res in results:
        if res['status'] == 'success':
            success_list.append(res)
        else:
            failed_list.append(res)

    return jsonify({
        "request_status": "completed",
        "total_processed": len(accounts),
        "success_count": len(success_list),
        "failed_count": len(failed_list),
        "success_list": success_list,
        "failed_list": failed_list
    })


if __name__ == '__main__':
    # Koyeb এর পোর্টের জন্য ডায়নামিক পোর্ট সেটআপ
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)