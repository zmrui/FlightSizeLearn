#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kobject.h>
#include <linux/sysfs.h>
#include <linux/fs.h>
#include <linux/string.h>
#include <linux/spinlock.h>
#include <linux/kprobes.h>
#include <net/tcp.h> // Required for struct tcp_sock and its members

// --- The shared data variables and their protection ---
// We will store the latest values from the target connection here.
static u32 latest_skb_data_len;
static u8  latest_icsk_ca_state;
static u32 latest_snd_cwnd;
static u32 latest_snd_ssthresh;
static u32 latest_packets_out;
static u32 latest_retrans_out;
static u32 latest_sacked_out;
static u32 latest_lost_out;
static u32 latest_prr_out;
static u32 latest_prr_delivered;
static u32 latest_tsoffset;
static u32 latest_rttvar_us;
static u32 latest_srtt_us;
static u32 latest_delivered;
static u32 latest_lost;
static u32 latest_total_retrans;
static u32 latest_reordering;
static u32 latest_rcv_wnd;
static u32 latest_reord_seen;
static u32 latest_segs_out;
static DEFINE_SPINLOCK(socket_info_lock); // Lock to protect the variables

// --- The 'kobject' that will represent our directory in /sys/kernel/ ---
static struct kobject *tcp_monitor_kobj;

// =========================================================================
// == SYSFS IMPLEMENTATION (THE "PRODUCER" FOR USERSPACE)                 ==
// =========================================================================

// --- 'show' function for the combined socket_info file ---
// This is called when a user reads /sys/kernel/tcp_monitor/socket_info
static ssize_t socket_info_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf)
{
    u32 temp_skb_data_len, temp_icsk_ca_state, temp_snd_cwnd, temp_snd_ssthresh, temp_packets_out, temp_retrans_out, temp_sacked_out, temp_lost_out, temp_prr_out, temp_prr_delivered, temp_tsoffset, temp_rttvar_us, temp_srtt_us, temp_delivered, temp_lost, temp_total_retrans, temp_reordering, temp_rcv_wnd, temp_reord_seen, temp_segs_out;

    // Lock, read all the values safely, and unlock
    spin_lock_bh(&socket_info_lock);
    temp_skb_data_len = latest_skb_data_len;
    temp_icsk_ca_state = latest_icsk_ca_state;
    temp_snd_cwnd = latest_snd_cwnd;
    temp_snd_ssthresh = latest_snd_ssthresh;
    temp_packets_out = latest_packets_out;
    temp_retrans_out = latest_retrans_out;
    temp_sacked_out = latest_sacked_out;
    temp_lost_out = latest_lost_out;
    temp_prr_out = latest_prr_out;
    temp_prr_delivered = latest_prr_delivered;
    temp_tsoffset = latest_tsoffset;
    temp_rttvar_us = latest_rttvar_us;
    temp_srtt_us = latest_srtt_us;
    temp_delivered = latest_delivered;
    temp_lost = latest_lost;
    temp_total_retrans = latest_total_retrans;
    temp_reordering = latest_reordering;
    temp_rcv_wnd = latest_rcv_wnd;
    temp_reord_seen = latest_reord_seen;
    temp_segs_out = latest_segs_out;
    spin_unlock_bh(&socket_info_lock);

    return sysfs_emit(buf, "%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u", 
            temp_icsk_ca_state, 	
            temp_snd_cwnd,
            temp_snd_ssthresh,
            temp_packets_out,
            temp_retrans_out,
            temp_sacked_out,
            temp_lost_out,
            temp_prr_out,
            temp_prr_delivered,
            temp_tsoffset,
            temp_rttvar_us,
            temp_srtt_us,
            temp_delivered,
            temp_lost,
            temp_total_retrans,
            temp_reordering,
            temp_rcv_wnd,
            temp_reord_seen,
            temp_segs_out
            );
}


// --- Link attribute to function and set permissions ---
// Creates one read-only file named "socket_info"
static struct kobj_attribute socket_info_attribute = __ATTR_RO(socket_info);

// A list of all attributes to create
static struct attribute *attrs[] = {
    &socket_info_attribute.attr,
    NULL, // Must be NULL-terminated
};

// The attribute group combines the attributes into one structure
static struct attribute_group attr_group = {
    .attrs = attrs,
};

// =========================================================================
// == KPROBE IMPLEMENTATION (THE "CONSUMER" OF KERNEL DATA)               ==
// =========================================================================

static struct kprobe kp = {
    .symbol_name = "tcp_ack",
};

// This handler runs AFTER tcp_ack completes.
static void handler_post(struct kprobe *p, struct pt_regs *regs, unsigned long flags)
{
    // The first argument to tcp_ack is 'struct sock *sk' (in regs->di)
    struct sock *sk = (struct sock *)regs->di;
    // NEW: The second argument is 'const struct sk_buff *skb' (in regs->si)
    const struct sk_buff *skb = (const struct sk_buff *)regs->si;
    struct tcp_sock *tp;
    struct inet_connection_sock *icsk;

    // A simple check to ensure we got valid pointers
    if (!sk || !skb)
        return;

    // We are interested only in connections to destination port 5201
    // if (sk->sk_dport == htons(5001)) {
    if (sk->sk_num == 5001) {
        tp = tcp_sk(sk);
        icsk = inet_csk(sk);

        // Safely update the shared variables
        spin_lock_bh(&socket_info_lock);
        latest_srtt_us = tp->srtt_us;
        latest_snd_cwnd = tp->snd_cwnd;
        latest_skb_data_len = skb->data_len;
        latest_icsk_ca_state = icsk->icsk_ca_state;
        latest_snd_ssthresh = tp->snd_ssthresh;
        latest_packets_out = tp->packets_out;
        latest_retrans_out = tp->retrans_out;
        latest_sacked_out = tp->sacked_out;
        latest_lost_out = tp->lost_out;
        latest_prr_out = tp->prr_out;
        latest_prr_delivered = tp->prr_delivered;
        latest_tsoffset = tp->tsoffset;
        latest_rttvar_us = tp->rttvar_us;
        latest_delivered = tp->delivered;
        latest_lost = tp->lost;
        latest_total_retrans = tp->total_retrans;
        latest_reordering = tp->reordering;
        latest_rcv_wnd = tp->rcv_wnd;
        latest_reord_seen = tp->reord_seen;
        latest_segs_out = tp->segs_out;
        spin_unlock_bh(&socket_info_lock);
        printk("tcp_monitor: Updated socket info, SRTT: %u, CWND: %u, ssthresh: %u, DataLen: %u, CA_STATE: %u\n", latest_srtt_us, latest_snd_cwnd, latest_snd_ssthresh, latest_skb_data_len, latest_icsk_ca_state);
    }
}

// =========================================================================
// == MODULE INIT AND EXIT                                                ==
// =========================================================================

static int __init tcp_monitor_init(void)
{
    int ret;
    pr_info("Loading TCP Monitor module\n");

    tcp_monitor_kobj = kobject_create_and_add("tcp_monitor", kernel_kobj);
    if (!tcp_monitor_kobj)
        return -ENOMEM;

    ret = sysfs_create_group(tcp_monitor_kobj, &attr_group);
    if (ret) {
        pr_err("tcp_monitor: failed to create sysfs group\n");
        kobject_put(tcp_monitor_kobj);
        return ret;
    }
    pr_info("tcp_monitor: Sysfs interface created.\n");

    // Register the kprobe
    kp.post_handler = handler_post;
    kp.pre_handler = NULL;

    ret = register_kprobe(&kp);
    if (ret < 0) {
        pr_err("tcp_monitor: failed to register kprobe on %s: %d\n", kp.symbol_name, ret);
        sysfs_remove_group(tcp_monitor_kobj, &attr_group);
        kobject_put(tcp_monitor_kobj);
        return ret;
    }
    pr_info("tcp_monitor: Kprobe registered on %s\n", kp.symbol_name);

    return 0;
}

static void __exit tcp_monitor_exit(void)
{
    unregister_kprobe(&kp);
    pr_info("tcp_monitor: Kprobe on %s unregistered\n", kp.symbol_name);

    sysfs_remove_group(tcp_monitor_kobj, &attr_group);
    kobject_put(tcp_monitor_kobj);

    pr_info("TCP Monitor module unloaded\n");
}

module_init(tcp_monitor_init);
module_exit(tcp_monitor_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("Exports TCP info to sysfs for dport 5201 after ACK processing");