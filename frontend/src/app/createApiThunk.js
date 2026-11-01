import { createAsyncThunk } from '@reduxjs/toolkit'
import { toErrorPayload } from '../services/apiClient'

/**
 * createAsyncThunk with one error rule for the whole app: a failed request is rejected
 * with a plain, serialisable payload {status, code, message, details, answerId}.
 *
 * Every slice reads errors the same way (action.payload), and the auth slice can spot a
 * 401 from ANY thunk and sign the user out.
 */
export function createApiThunk(type, request) {
  return createAsyncThunk(type, async (arg, { rejectWithValue }) => {
    try {
      return await request(arg)
    } catch (error) {
      return rejectWithValue(toErrorPayload(error))
    }
  })
}
