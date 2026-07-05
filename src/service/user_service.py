from googleapiclient.discovery import build
import traceback
import logging

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
def get_user_info_service(creds):
    """
    使用 People API 從 Google 帳戶取得使用者名稱與 email。
    """
    try:
        service = build('people', 'v1', credentials=creds)
        profile = service.people().get(
            resourceName='people/me',
            personFields='names,emailAddresses'
        ).execute()

        name = profile.get('names', [{}])[0].get('displayName')
        email = profile.get('emailAddresses', [{}])[0].get('value')

        return {
            "name": name,
            "email": email
        }

    except Exception as e:
        logging.error(f"get_user_info_service failed: {e}\n{traceback.format_exc()}")
        return {
            "error": f"無法取得使用者資訊: {str(e)}"
        }
