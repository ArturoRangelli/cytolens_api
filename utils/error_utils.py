from botocore.exceptions import ClientError
from flask import jsonify
from flask_jwt_extended import JWTManager
from marshmallow import ValidationError


def _jsonapi_error(
    status: int,
    title: str,
    detail: str,
    pointer: str | None = None,
    code: str | None = None,
):
    error = {"status": str(status), "title": title, "detail": detail}
    if pointer:
        error["source"] = {"pointer": pointer}
    if code:
        error["code"] = code
    return jsonify({"errors": [error]}), status


def register_error_handlers(app, jwt: JWTManager):
    # AWS Errors
    @app.errorhandler(ClientError)
    def handle_aws_client_error(e):
        code = e.response["Error"]["Code"]
        message = e.response["Error"]["Message"]
        return _jsonapi_error(
            status=502,
            title=f"AWS ClientError: {code}",
            detail=message,
            code="aws_client_error",
        )

    # Marshmallow Errors
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        print("ValidationError:", e)
        return (
            jsonify(
                {
                    "errors": [
                        {
                            "status": "400",
                            "source": {"pointer": f"/{field}"},
                            "title": "Invalid Attribute",
                            "detail": msg,
                            "code": "validation_error",
                        }
                        for field, messages in e.messages.items()
                        for msg in messages
                    ]
                }
            ),
            400,
        )

    @app.errorhandler(ValueError)
    def handle_value_error(e):
        print("ValueError:", e)
        return _jsonapi_error(
            status=409, title="Invalid Value", detail=str(e), code="value_error"
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        print("Exception:", e)
        return _jsonapi_error(
            status=500,
            title="Internal Server Error",
            detail="An unexpected error occurred.",
            code="internal_error",
        )

    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return _jsonapi_error(
            status=401,
            title="Missing or invalid token",
            detail=reason,
            code="unauthorized",
        )

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return _jsonapi_error(
            status=401, title="Invalid token", detail=reason, code="invalid_token"
        )

    @jwt.expired_token_loader
    def handle_expired_token(jwt_header, jwt_data):
        return _jsonapi_error(
            status=401,
            title="Expired token",
            detail="Your session has expired. Please log in again.",
            code="token_expired",
        )

    @jwt.revoked_token_loader
    def handle_revoked_token(jwt_header, jwt_data):
        return _jsonapi_error(
            status=401,
            title="Revoked token",
            detail="This token has been revoked.",
            code="token_revoked",
        )

    @jwt.needs_fresh_token_loader
    def handle_needs_fresh(jwt_header, jwt_data):
        return _jsonapi_error(
            status=401,
            title="Fresh token required",
            detail="You must re-authenticate to access this resource.",
            code="token_fresh_required",
        )
