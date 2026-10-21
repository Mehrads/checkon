import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type SetPasswordProps = {
  project_name: string
  username: string
  plan: string
  link: string
  login_link: string
  valid_hours: string
}

// Sent when a completed Checkout creates the account. The link is a password-reset link.
export default function SetPassword({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  plan = "{{ plan }}",
  link = "{{ link }}",
  login_link = "{{ login_link }}",
  valid_hours = "{{ valid_hours }}",
}: SetPasswordProps) {
  return (
    <Layout
      title={`Set your ${project_name} password`}
      preview={`Your ${project_name} ${plan} is ready. Set a password to sign in.`}
      project_name={project_name}
    >
      <Heading>Welcome to {project_name}</Heading>
      <Text style={bodyTextStyle}>Hi {username},</Text>
      <Text style={bodyTextStyle}>
        Thanks for subscribing. Your {plan} is ready. Set a password to sign in
        and start checking postings:
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
        If you didn't subscribe to {project_name}, reply to this email and we'll
        sort it out.
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
