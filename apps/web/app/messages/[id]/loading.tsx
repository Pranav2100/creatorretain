import { Bone, ChromeBone } from "@/components/skeleton";

/**
 * A thread, so not the usual title-then-list shape: who you are
 * talking to across the top, the conversation in the middle, and
 * something to type in at the bottom.
 *
 * The bubbles alternate sides and vary in width because that is
 * what a conversation looks like; a column of identical blocks
 * would read as a list.
 */
const BUBBLES: { mine: boolean; width: string; lines: number }[] = [
  { mine: false, width: "62%", lines: 2 },
  { mine: true, width: "45%", lines: 1 },
  { mine: false, width: "38%", lines: 1 },
  { mine: true, width: "58%", lines: 2 },
  { mine: false, width: "50%", lines: 1 },
];

export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading">
      <ChromeBone />

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-28">
        {/* Who it is with, and the way back. */}
        <Bone className="mt-10 h-3 w-20 rounded" />
        <Bone className="mt-4 h-7 w-[14rem] rounded" />
        <Bone className="mt-2.5 h-3 w-[9rem] rounded" />

        <div className="mt-8 space-y-4 border-t border-line pt-7">
          {BUBBLES.map((bubble, index) => (
            <div
              key={index}
              className={bubble.mine ? "flex justify-end" : "flex"}
            >
              <div
                className="rounded-[14px] border border-line bg-surface p-3.5"
                style={{ width: bubble.width }}
              >
                {Array.from({ length: bubble.lines }).map((_, line) => (
                  <Bone
                    key={line}
                    className={`h-3 rounded ${line > 0 ? "mt-2" : ""}`}
                    style={{ width: line > 0 ? "70%" : "100%" }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* The composer. */}
        <div className="mt-8 border-t border-line pt-5">
          <Bone className="h-[72px] w-full rounded-lg" />
          <Bone className="mt-3 ml-auto h-[38px] w-[6.5rem] rounded-lg" />
        </div>
      </main>
    </div>
  );
}
