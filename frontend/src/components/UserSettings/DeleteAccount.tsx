import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  return (
    <div className="max-w-md mt-4 rounded-lg border border-destructive/50 p-4">
      <h3 className="font-semibold text-destructive">Delete Account</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Permanently delete your account and all associated data, including your
        archive of approved postings. Download it from Archive first if you need
        the records.
      </p>
      <DeleteConfirmation />
    </div>
  )
}

export default DeleteAccount
