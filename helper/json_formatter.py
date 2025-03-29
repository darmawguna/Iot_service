from flask import jsonify

def create_response(status=True, message="Success", data=None, extra_message=None, status_code=200):
    """
    Helper untuk membuat format response JSON yang lebih fleksibel.
    
    :param status: Status request (default: True)
    :param message: Pesan utama response (default: "Success")
    :param data: Data hasil request (default: None)
    :param extra_message: Pesan tambahan opsional di dalam data
    :param status_code: HTTP status code (default: 200)
    :return: Response JSON Flask dengan format standar
    """
    response = {
        "status": status,
        "message": message,
        "data": data if data else {},
    }

    # Jika ada extra_message, tambahkan ke dalam response
    if extra_message:
        response["extra_message"] = extra_message

    return jsonify(response), status_code
