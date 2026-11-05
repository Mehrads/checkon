// Opens the CheckON side panel from the toolbar button or the right-click menu.
// Nothing is checked here: the side panel sends the posting to the CheckON API it was built for.
//
// The toolbar click is handled here rather than with setPanelBehavior({ openPanelOnActionClick }):
// a click Chrome handles itself opens the panel but grants no activeTab access, so the panel
// couldn't read the page. Handling the click grants it for the current tab.

const MENU_ID = "checkon-check"

/** Open the panel in the tab's window, then ask it to read that tab. Both calls stay inside the
 * click, which is the user gesture sidePanel.open needs. */
function openFor(tab: chrome.tabs.Tab, selection = "") {
  if (tab.id === undefined) return
  chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {})
  chrome.storage.session.set({
    request: { tabId: tab.id, selection, at: Date.now() },
  })
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Check with CheckON",
    contexts: ["selection", "editable"],
  })
})

chrome.action.onClicked.addListener((tab) => openFor(tab))

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === MENU_ID && tab) openFor(tab, info.selectionText)
})
