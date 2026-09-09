# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .dataset_store import BoardDatasetStore

BASE_DIR = Path(__file__).resolve().parents[2]
BOARDS_DIR = BASE_DIR / 'boards'
TEMPLATES_DIR = BASE_DIR / 'templates'
APP_DIR = BASE_DIR / 'apps' / 'roi-editor'

store = BoardDatasetStore(BOARDS_DIR)
app = FastAPI(title='Board ROI Editor Backend')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

if APP_DIR.exists():
    app.mount('/static', StaticFiles(directory=str(APP_DIR)), name='static')


class SaveBoardRequest(BaseModel):
    board_id: str
    name: str
    reference_image_path: str
    rois: List[Dict[str, Any]]


@app.get('/')
def root() -> HTMLResponse:
    index_path = APP_DIR / 'index.html'
    if not index_path.exists():
        raise HTTPException(status_code=404, detail='ROI editor UI not found')
    return HTMLResponse(index_path.read_text(encoding='utf-8'))


@app.get('/api/health')
def health() -> dict:
    return {'status': 'ok'}


@app.get('/api/boards')
def list_boards() -> dict:
    return {'boards': store.list_boards()}


@app.get('/api/boards/{board_id}')
def get_board(board_id: str) -> dict:
    try:
        board = store.get_board(board_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    ref_abs = Path(board.get('reference_image_path', ''))
    if ref_abs.exists() and ref_abs.is_file():
        board['reference_image_url'] = f'/api/boards/{board_id}/reference-image'
    return board


@app.get('/api/boards/{board_id}/reference-image')
def get_board_reference_image(board_id: str):
    try:
        board = store.get_board(board_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    ref_abs = Path(board.get('reference_image_path', ''))
    if not ref_abs.exists() or not ref_abs.is_file():
        raise HTTPException(status_code=404, detail=f'Reference image not found for board {board_id}')
    return FileResponse(str(ref_abs))


@app.post('/api/boards/save')
def save_board(request: SaveBoardRequest) -> JSONResponse:
    try:
        result = store.save_board_with_rois(request.board_id, request.name, request.reference_image_path, request.rois)
        return JSONResponse({'status': 'ok', **result})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/boards/{board_id}/export-template')
def export_template(board_id: str) -> dict:
    try:
        out = store.export_board_to_template(board_id, TEMPLATES_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {'status': 'ok', 'template_path': str(out)}
