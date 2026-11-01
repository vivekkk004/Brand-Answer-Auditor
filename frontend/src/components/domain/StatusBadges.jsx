import {
  ACTIVE_RUN_STATUSES,
  ANSWER_STATUS_TONE,
  LABEL_TONE,
  REVIEW_STATUS_TONE,
  RUN_STATUS_TONE,
} from '../../utils/constants'
import { humanize } from '../../utils/format'
import Badge from '../ui/Badge'

export function RunStatusBadge({ status }) {
  return (
    <Badge tone={RUN_STATUS_TONE[status] || 'slate'} dot pulse={ACTIVE_RUN_STATUSES.includes(status)}>
      {humanize(status)}
    </Badge>
  )
}

export function AnswerStatusBadge({ status }) {
  return (
    <Badge tone={ANSWER_STATUS_TONE[status] || 'slate'} dot>
      {humanize(status)}
    </Badge>
  )
}

export function LabelBadge({ label }) {
  return <Badge tone={LABEL_TONE[label] || 'slate'}>{humanize(label)}</Badge>
}

export function ReviewStatusBadge({ status }) {
  return (
    <Badge tone={REVIEW_STATUS_TONE[status] || 'slate'} dot>
      {humanize(status)}
    </Badge>
  )
}
