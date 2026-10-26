import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type FreeAccountProps = {
  project_name: string
  username: string
  checks: string
  saved: string
  link: string
  login_link: string
  valid_hours: string
}

// Sent when someone signs up for a free account. The link is a password-reset link, so it also proves the address.
// `saved` is a sentence about the report the account will keep, or empty.
export default function FreeAccount({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  checks = "{{ checks }}",
  saved = "{{ saved }}",
  link = "{{ link }}",
  login_link = "{{ login_link }}",
  valid_hours = "{{ valid_hours }}",
}: FreeAccountProps) {
  return (
    <Layout
      title={`Set your ${project_name} password`}
      preview={`Your free ${project_name} account is ready. Set a password to sign in.`}
      project_name={project_name}
    >
      <Heading>Welcome to {project_name}</Heading>
      <Text style={bodyTextStyle}>Hi {username},</Text>
      <Text style={bodyTextStyle}>
        Your free account is ready: {checks} checks every 30 days, and a history
        of what you checked. {saved} Set a password to sign in:
      </Text>
      <LinkButton href={link}>Set password</LinkButton>
      <Text style={supportingTextStyle}>
        Or copy and paste this link into your browser:
        <br />
        <Link href={link}>{link}</Link>
      </Text>
      <Text style={supportingTextStyle}>
        This link will expire in {valid_hours} hours. After that, use "Forgot
        your password?" on the <Link href={login_link}>sign-in page</Link>.
      </Text>
      <Text style={supportingTextStyle}>
        If you didn't sign up for {project_name}, ignore this email: without a
        password, nobody can use the account.
      </Text>
    </Layout>
  )
}

const bodyTextStyle = {
  color: "#334155",
  fontSize: "15px",
  lineHeight: "26px",
  margin: "0 0 18px",
}

const supportingTextStyle = {
  color: "#64748b",
  fontSize: "14px",
  lineHeight: "23px",
  margin: "0 0 16px",
}
