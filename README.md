# commute-trains

Fetches live High Brooms <-> London Bridge departures from the Rail Data Marketplace on weekday commute windows and publishes them as `departures.json` on the `data` branch.

Readers (Claude scheduled tasks, the Daily Commute board) fetch:

    https://raw.githubusercontent.com/<owner>/commute-trains/data/departures.json

## Setup

- Secret `RDM_API_KEY`: consumer key from the RDM "Live Arrival and Departure Boards" subscription.
- Variable `RDM_BOARD_URL`: the board endpoint up to the method name, from the subscription page, e.g.
  `https://api1.raildata.org.uk/1010-live-arrival-and-departure-boards-arr-and-dep1_1/LDBWS/api/20220120/GetArrDepBoardWithDetails`

The key is only ever read by the workflow. Nothing in this repo or the published JSON contains it.

## Output

Each board carries `ok`, `generatedAt` (from Darwin) and either `trains` or `error`. The top-level `fetchedAt` is when the workflow ran; readers should treat data more than ~15 minutes old as stale, since GitHub scheduled runs are often late.
