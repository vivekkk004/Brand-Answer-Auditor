import { createSlice } from '@reduxjs/toolkit'
import { createApiThunk } from '../../app/createApiThunk'
import { verifyText as verifyTextRequest } from '../../services/verifyService'

export const verifyText = createApiThunk('verify/verifyText', (input) => verifyTextRequest(input))

const initialState = { status: 'idle', result: null, error: null }

const verifySlice = createSlice({
  name: 'verify',
  initialState,
  reducers: {
    resetVerify() {
      return initialState
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(verifyText.pending, (state) => {
        state.status = 'loading'
        state.result = null
        state.error = null
      })
      .addCase(verifyText.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.result = action.payload
      })
      // The error keeps answerId: the failed attempt is saved and can be opened.
      .addCase(verifyText.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload
      })
  },
})

export const { resetVerify } = verifySlice.actions
export default verifySlice.reducer
