import Spinner from './Spinner'

/** A centred spinner with a label, for a page or panel that is still loading. */
export default function LoadingState({ label = 'Loading…', className = 'py-14' }) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <Spinner className="h-5 w-5 text-indigo-600" label={label} />
    </div>
  )
}
