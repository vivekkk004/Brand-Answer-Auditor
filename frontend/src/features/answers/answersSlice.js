import { createSlice } from '@reduxjs/toolkit'
import { createApiThunk } from '../../app/createApiThunk'
import { getAnswer } from '../../services/answersService'

export const fetchAnswer = createApiThunk('answers/fetchOne', (answerId) => getAnswer(answerId))

const answersSlice = createSlice({
  name: 'answers',
  initialState: { byId: {}, status: 'idle', error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchAnswer.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchAnswer.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.byId[action.payload.id] = action.payload
      })
      .addCase(fetchAnswer.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload
      })
  },
})

export default answersSlice.reducer

export const selectAnswerById = (answerId) => (state) => state.answers.byId[answerId]
