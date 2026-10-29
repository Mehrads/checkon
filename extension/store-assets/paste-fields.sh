#!/bin/bash
# Puts each Chrome Web Store field on the clipboard in turn: paste it into the field named, come back here and
# press Return for the next one.
set -u
fields=(
  "PRIVACY TAB > Single purpose description|CheckON checks the job posting you are writing against Ontario's job posting rules, and writes the fixes you accept back into the job form."
  "PRIVACY TAB > sidePanel justification|The check runs in Chrome's side panel, next to the job form the user is editing."
  "PRIVACY TAB > activeTab justification|When the user clicks the CheckON icon or the \"Check with CheckON\" menu item, CheckON reads the job posting (or the application form's questions) from that tab and writes the fixes the user accepts back into the job form. It acts only on that tab, and only after the click."
  "PRIVACY TAB > scripting justification|Runs CheckON's own packaged code in the tab the user clicked CheckON on, to read the posting from the page's editor, highlight the problems in it, and insert the fixes the user accepts. No remote code is used."
  "PRIVACY TAB > contextMenus justification|Adds a right-click \"Check with CheckON\" item so the user can check text they have selected."
  "PRIVACY TAB > storage justification|Session storage passes a right-click request to the side panel and is cleared when the browser closes. Local storage keeps a paying customer signed in until they log out."
  "PRIVACY TAB > Host permission justification|Sends the posting the user asked to check to CheckON's own API at https://checkon.ca, which returns the results and the fixes. No other sites are contacted."
  "PRIVACY TAB > Privacy policy URL|https://checkon.ca/privacy"
  "SETTINGS PAGE > Contact email (then click Verify)|info@checkon.ca"
)
total=${#fields[@]}
for i in "${!fields[@]}"; do
  label=${fields[$i]%%|*}
  text=${fields[$i]#*|}
  printf '%s' "$text" | pbcopy
  printf '\n[%d/%d] Copied for: %s\n' "$((i + 1))" "$total" "$label"
  [ "$((i + 1))" -lt "$total" ] && read -r -p "Paste it there, then press Return for the next one... " _
done
cat <<'EOF'

All fields copied. Still to click on the Privacy tab:
  - Remote code: "No, I am not using remote code"
  - Data usage: tick Personally identifiable information, Authentication information, Website content
  - Tick the three certifications, then Save draft
Then verify the email Google sends to info@checkon.ca, and click Submit for review.
EOF
