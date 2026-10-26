# Making a sample report

The reports in `samples/` are real runs with names replaced. Numbers, findings and wording are left as they are. To add or refresh one:

1. Run `/kubegap` or `/kubegap full` and find the snapshot folder it names at the bottom of `report.md`.
2. Copy `report.md` and `report-details.md` out of the snapshot.
3. Mask tokens, account ids and private IPs in place:

   ```bash
   scripts/kubegap mask --ips report.md report-details.md
   ```

4. Replace names with placeholders. The map file is yours and is not committed; the format is in the header of `scripts/scrub-sample.py`. Every hostname in the `hosts` list gets a placeholder of its own, so two hosts never end up with the same name:

   ```bash
   scripts/scrub-sample.py --map ~/.kubegap/scrub-map.yaml report.md         samples/<lang>/<cluster>/<mode>/report.md
   scripts/scrub-sample.py --map ~/.kubegap/scrub-map.yaml report-details.md samples/<lang>/<cluster>/<mode>/report-details.md
   ```

5. Read both files once. Anything the map missed goes into the map, not into a hand edit, so the next refresh gets it too.
6. Add the row to `samples/README.md`.

Folder rule: `samples/<lang>/<cluster>/<mode>/` with `lang` in `en`, `ko`; `cluster` in `eks`, `k3s`; `mode` in `daily`, `full`.
