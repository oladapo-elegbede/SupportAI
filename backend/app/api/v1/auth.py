from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthUserResponse,
    TokenResponse,
)
from app.services.auth import (
    AuthService,
    AuthError,
    InvalidCredentialsError,
    InvalidTokenError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/"


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    is_secure = settings.APP_ENV != "development"
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        httponly=True,
        max_age=max_age,
        samesite="lax",
        secure=is_secure,
        path=COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    is_secure = settings.APP_ENV != "development"
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=is_secure,
    )


@router.post(
    "/register",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new organization and owner user",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthUserResponse:
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_organization_and_owner(request)
        return AuthUserResponse.model_validate(user)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and receive access token",
)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(db)
    try:
        user = await auth_service.authenticate_user(request.email, request.password)
        access_token, raw_refresh_token = await auth_service.create_session(user)
        
        set_refresh_cookie(response, raw_refresh_token)
        
        return TokenResponse(access_token=access_token, token_type="bearer")
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token cookie and receive new access token",
)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    try:
        access_token, new_raw_token = await auth_service.refresh_session(raw_token)
        
        set_refresh_cookie(response, new_raw_token)
        
        return TokenResponse(access_token=access_token, token_type="bearer")
    except InvalidTokenError as e:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke refresh token and clear cookie",
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(COOKIE_NAME)
    if raw_token:
        auth_service = AuthService(db)
        await auth_service.logout(raw_token)
    
    clear_refresh_cookie(response)
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=AuthUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> AuthUserResponse:
    return AuthUserResponse.model_validate(current_user)
