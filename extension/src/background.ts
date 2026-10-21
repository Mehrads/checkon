// Opens the CheckON side panel from the toolbar button or the right-click menu.
// Nothing is checked here: the side panel sends the posting to checkon.ca.

const MENU_ID = "checkon-check"

function openOnToolbarClick() {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch(() => {})
}

chrome.runtime.onInstalled.addListener(() => {
  openOnToolbarClick()
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Check with CheckON",
    contexts: ["selection", "editable"],
  })
})

chrome.runtime.onStartup.addListener(openOnToolbarClick)

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID || tab?.id === undefined) return
  // Open first: the click is the user gesture that sidePanel.open needs.
  chrome.sidePanel.open({ tabId: tab.id }).catch(() => {})
  // The panel reads this and re-reads the page, so the selection is picked up whether or not it was open.
  chrome.storage.session.set({
    request: {
      tabId: tab.id,
      selection: info.selectionText ?? "",
      at: Date.now(),
    },
  })
})
