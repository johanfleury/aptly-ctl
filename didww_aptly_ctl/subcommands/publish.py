import logging
from pprint import pprint
from didww_aptly_ctl.utils.ExtendedAptlyClient import ExtendedAptlyClient
from didww_aptly_ctl.exceptions import DidwwAptlyCtlError
from didww_aptly_ctl.utils import PubSpec
from aptly_api.base import AptlyAPIException

logger = logging.getLogger(__name__)

def config_subparser(subparsers_action_object):
    parser_publish = subparsers_action_object.add_parser("publish",
            help="Administer publishes.",
            description="Administer publishes.")
    subparsers = parser_publish.add_subparsers()

    parser_list = subparsers.add_parser("list", help="List publishes")
    parser_list.set_defaults(func=list)
    parser_list.add_argument("--detail", action="store_true", help="Print additional details")

    parser_publish = subparsers.add_parser("publish", aliases=["create"], help="Publish snapshot/local repo")
    parser_publish.set_defaults(func=publish)
    parser_publish.add_argument("name", metavar="PUB_SPEC", help="Publish to create. See 'publish' subcommand --help")
    parser_publish.add_argument("-s", "--source-kind", choices=["local", "snapshot"], required=True,
            help="Publish from snapshots or local repos")
    parser_publish.add_argument("--architectures", default="", help="Coma separated list of architectures to publish")
    parser_publish.add_argument("--label", default=None, help="Value of 'Label:' field in published repository stanza")
    parser_publish.add_argument("--origin", default=None, help="Value of 'Origin:' field in published repository stanza")
    parser_publish.add_argument("-f", "--force", action="store_true",
            help="Overwrite files in pool/ directory without notice")
#    parser_publish.add_argument("--not-automatic", action="store_true",.
#            help="Indicates to the package manager to not install or upgrade packages from the repository without user consent").
#    parser_publish.add_argument("--but-automatic-upgrades", action="store_true",.
#            help="Excludes upgrades from the --not-automatic setting").
#    parser_publish.add_argument("--stkip-cleanup", action="store_true",.
#            help="Don’t remove unreferenced files in prefix/component").
    parser_publish.add_argument("sources", metavar="source", nargs="+",
            help="""A local repo or snapshot to publish from of the form 'name=component'.
            Component can be omitted, then it is taken from default
            component of repo/snaphost, or set to 'main'
            """)

    parser_update = subparsers.add_parser("update", help="Update published local repo or switch published snapshot")
    parser_update.set_defaults(func=update)
    parser_update.add_argument("name", metavar="PUB_SPEC", help="Publish to update. See 'publish' subcommand --help")
    parser_update.add_argument("-f", "--force", action="store_true",
            help="Overwrite files in pool/ directory without notice")

    parser_drop = subparsers.add_parser("drop", help="Drop published repository")
    parser_drop.set_defaults(func=drop)
    parser_drop.add_argument("name", metavar="PUB_SPEC", help="Publish to drop. See 'publish' subcommand --help")
    parser_drop.add_argument("-f", "--force", action="store_true", help="Delete publishesitory even if it has snapshots")


def pprint_publish(pub):
    print(PubSpec(pub.distribution, pub.prefix))
    print("    Source kind: " + pub.source_kind)
    print("    Prefix: " + pub.prefix)
    print("    Distribution: " + pub.distribution)
    print("    Storage: " + pub.storage)
    print("    Label: " + pub.label)
    print("    Origin: " + pub.origin)
    print("    Architectures: " + ", ".join(pub.architectures))
    print("    Sources:")
    for s in pub.sources:
        print(" "*8 + "{} ({})".format(s["Name"], s["Component"]))


def list(config, args):
    aptly = ExtendedAptlyClient(config.url)
    publish_list = aptly.publish.list()
    publish_list.sort(key=lambda p: repr(PubSpec(p.distribution, p.prefix)))
    for p in publish_list:
        if args.detail:
            pprint_publish(p)
        else:
            print(PubSpec(p.distribution, p.prefix))
    return 0


def update(config, args):
    aptly = ExtendedAptlyClient(config.url)
    try:
        p = PubSpec(args.name)
    except ValueError as e:
        raise DidwwAptlyCtlError("PUB_SPEC '%s' invalid. See 'publish' subcommand --help" % args.name) from e
    s_cfg = config.get_signing_config(p).as_dict(prefix="sign_")
    try:
        result = aptly.publish.update(
                prefix=p.prefix,
                distribution=p.distribution,
                force_overwrite=args.force,
                **s_cfg
                )
    except AptlyAPIException as e:
        if e.status_code == 404:
            raise DidwwAptlyCtlError(e) from e
        else:
            raise
    logger.debug("Api returned: " + str(result))
    pprint_publish(result)
    return 0


def publish(config, args):
    aptly = ExtendedAptlyClient(config.url)
    try:
        p = PubSpec(args.name)
    except ValueError as e:
        raise DidwwAptlyCtlError("PUB_SPEC '%s' invalid. See 'publish' subcommand --help" % args.name) from e
    s_cfg = config.get_signing_config(p).as_dict(prefix="sign_")
    architectures = args.architectures.split(',')
    sources = []
    for s in args.sources:
        name, sep, comp = s.partition('=')
        if len(name) == 0:
            raise DidwwAptlyCtlError
        elif len(comp) == 0:
            sources.append({"Name": name})
        else:
            sources.append({"Name": name, "Component": comp})
    try:
        result = aptly.publish.publish(
                prefix=p.prefix,
                distribution=p.distribution,
                source_kind=args.source_kind,
                sources=sources,
                architectures=architectures,
                label=args.label,
                origin=args.origin,
                force_overwrite=args.force,
                **s_cfg
                )
    except AptlyAPIException as e:
        raise DidwwAptlyCtlError(e) from e
    pprint_publish(result)
    return 0


def drop(config, args):
    aptly = ExtendedAptlyClient(config.url)
    try:
        p = PubSpec(args.name)
    except ValueError as e:
        raise DidwwAptlyCtlError("PUB_SPEC '%s' invalid. See 'publish' subcommand --help" % args.name) from e
    s_cfg = config.get_signing_config(p).as_dict(prefix="sign_")
    try:
        aptly.publish.drop(prefix=p.prefix, distribution=p.distribution, force_delete=args.force)
    except AptlyAPIException as e:
        raise DidwwAptlyCtlError(e) from e
    return 0

