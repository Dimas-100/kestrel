import { Mark } from '../components/Icon'

/** An honest placeholder for a page a later phase builds. */
export function Soon({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h1 className="text-[28px] font-semibold tracking-[-0.025em]">{title}</h1>
      <div className="panel mt-5 items-center text-center py-16 gap-3">
        <Mark size={28} />
        <p className="text-ink2 max-w-md">{text}</p>
      </div>
    </div>
  )
}
