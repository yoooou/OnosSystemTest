"""
Description: This test is to determine if ONOS can handle
             dynamic swapping of cluster nodes.

List of test cases:
CASE1: Compile ONOS and push it to the test machines
CASE2: Assign devices to controllers
CASE21: Assign mastership to controllers
CASE3: Assign intents
CASE4: Ping across added host intents
CASE5: Reading state of ONOS
CASE6: Swap nodes
CASE7: Check state after control plane failure
CASE8: Compare topo
CASE9: Link s3-s28 down
CASE10: Link s3-s28 up
CASE11: Switch down
CASE12: Switch up
CASE13: Clean up
CASE14: start election app on all onos nodes
CASE15: Check that Leadership Election is still functional
CASE16: Install Distributed Primitives app
CASE17: Check for basic functionality with distributed primitives
"""
class HAswapNodes:

    def __init__( self ):
        self.default = ''

    def CASE1( self, main ):
        """
        CASE1 is to compile ONOS and push it to the test machines

        Startup sequence:
        cell <name>
        onos-verify-cell
        NOTE: temporary - onos-remove-raft-logs
        onos-uninstall
        start mininet
        git pull
        mvn clean install
        onos-package
        onos-install -f
        onos-wait-for-start
        start cli sessions
        start tcpdump
        """
        import time
        import os
        import re
        main.log.info( "ONOS HA test: Restart all ONOS nodes - " +
                         "initialization" )
        # set global variables
        # These are for csv plotting in jenkins
        main.HAlabels = []
        main.HAdata = []
        try:
            from tests.dependencies.ONOSSetup import ONOSSetup
            main.testSetUp = ONOSSetup()
        except ImportError:
            main.log.error( "ONOSSetup not found. exiting the test" )
            main.exit()
        main.testSetUp.envSetupDescription()
        try:
            from tests.HA.dependencies.HA import HA
            main.HA = HA()
            from tests.HA.HAswapNodes.dependencies.Server import Server
            main.Server = Server()
            # load some variables from the params file
            cellName = main.params[ 'ENV' ][ 'cellName' ]
            main.apps = main.params[ 'ENV' ][ 'appString' ]
            main.numCtrls = int( main.params[ 'num_controllers' ] )
            if main.ONOSbench.maxNodes and\
                        main.ONOSbench.maxNodes < main.numCtrls:
                main.numCtrls = int( main.ONOSbench.maxNodes )
            main.maxNodes = main.numCtrls
            stepResult = main.testSetUp.envSetup( hasNode=True )
        except Exception as e:
            main.testSetUp.envSetupException( e )
        main.testSetUp.evnSetupConclusion( stepResult )
        main.HA.generateGraph( "HAswapNodes" )


        main.testSetUp.ONOSSetUp( main.Mininet1, cellName=cellName, removeLog=True,
                                 extraApply=main.HA.customizeOnosService,
                                 arg=main.HA.swapNodeMetadata,
                                 extraClean=main.HA.cleanUpOnosService,
                                 installMax=True )
        main.HA.initialSetUp()

    def CASE2( self, main ):
        """
        Assign devices to controllers
        """
        main.HA.assignDevices( main )

    def CASE21( self, main ):
        """
        Assign mastership to controllers
        """
        main.HA.assignMastership( main )

    def CASE3( self, main ):
        """
        Assign intents
        """
        main.HA.assignIntents( main )

    def CASE4( self, main ):
        """
        Ping across added host intents
        """
        main.HA.pingAcrossHostIntent( main, True, True )

    def CASE5( self, main ):
        """
        Reading state of ONOS
        """
        main.HA.readingState( main )

    def CASE6( self, main ):
        """
        The Scaling case.
        """
        import time
        import re
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        assert main.CLIs, "main.CLIs not defined"
        assert main.nodes, "main.nodes not defined"
        try:
            main.HAlabels
        except ( NameError, AttributeError ):
            main.log.error( "main.HAlabels not defined, setting to []" )
            main.HAlabels = []
        try:
            main.HAdata
        except ( NameError, AttributeError ):
            main.log.error( "main.HAdata not defined, setting to []" )
            main.HAdata = []

        main.case( "Swap some of the ONOS nodes" )

        main.step( "Checking ONOS Logs for errors" )
        for i in main.activeNodes:
            node = main.nodes[ i ]
            main.log.debug( "Checking logs for errors on " + node.name + ":" )
            main.log.warn( main.ONOSbench.checkLogs( node.ip_address ) )

        main.step( "Generate new metadata file" )
        old = [ main.activeNodes[ 1 ], main.activeNodes[ -2 ] ]
        new = range( main.ONOSbench.maxNodes )[ -2: ]
        assert len( old ) == len( new ), "Length of nodes to swap don't match"
        handle = main.ONOSbench.handle
        for x, y in zip( old, new ):
            handle.sendline( "export OC{}=$OC{}".format( x + 1, y + 1 ) )
            handle.expect( "\$" )  # from the variable
            ret = handle.before
            handle.expect( "\$" )  # From the prompt
            ret += handle.before
            main.log.debug( ret )
            main.activeNodes.remove( x )
            main.activeNodes.append( y )

        genResult = main.Server.generateFile( main.numCtrls )
        utilities.assert_equals( expect=main.TRUE, actual=genResult,
                                 onpass="New cluster metadata file generated",
                                 onfail="Failled to generate new metadata file" )
        time.sleep( 5 )  # Give time for nodes to read new file

        main.step( "Start new nodes" )  # OR stop old nodes?
        started = main.TRUE
        for i in new:
            started = main.ONOSbench.onosStart( main.nodes[ i ].ip_address ) and main.TRUE
        utilities.assert_equals( expect=main.TRUE, actual=started,
                                 onpass="ONOS started",
                                 onfail="ONOS start NOT successful" )

        main.step( "Checking if ONOS is up yet" )
        for i in range( 2 ):
            onosIsupResult = main.TRUE
            for i in main.activeNodes:
                node = main.nodes[ i ]
                main.ONOSbench.onosSecureSSH( node=node.ip_address )
                started = main.ONOSbench.isup( node.ip_address )
                if not started:
                    main.log.error( node.name + " didn't start!" )
                onosIsupResult = onosIsupResult and started
            if onosIsupResult == main.TRUE:
                break
        utilities.assert_equals( expect=main.TRUE, actual=onosIsupResult,
                                 onpass="ONOS started",
                                 onfail="ONOS start NOT successful" )

        main.step( "Starting ONOS CLI sessions" )
        cliResults = main.TRUE
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[ i ].startOnosCli,
                             name="startOnosCli-" + str( i ),
                             args=[ main.nodes[ i ].ip_address ] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            cliResults = cliResults and t.result
        utilities.assert_equals( expect=main.TRUE, actual=cliResults,
                                 onpass="ONOS cli started",
                                 onfail="ONOS clis did not start" )

        main.step( "Checking ONOS nodes" )
        nodeResults = utilities.retry( main.HA.nodesCheck,
                                       False,
                                       args=[ main.activeNodes ],
                                       attempts=5 )
        utilities.assert_equals( expect=True, actual=nodeResults,
                                 onpass="Nodes check successful",
                                 onfail="Nodes check NOT successful" )

        for i in range( 10 ):
            ready = True
            for i in main.activeNodes:
                cli = main.CLIs[ i ]
                output = cli.summary()
                if not output:
                    ready = False
            if ready:
                break
            time.sleep( 30 )
        utilities.assert_equals( expect=True, actual=ready,
                                 onpass="ONOS summary command succeded",
                                 onfail="ONOS summary command failed" )
        if not ready:
            main.cleanup()
            main.exit()

        # Rerun for election on new nodes
        runResults = main.TRUE
        for i in main.activeNodes:
            cli = main.CLIs[ i ]
            run = cli.electionTestRun()
            if run != main.TRUE:
                main.log.error( "Error running for election on " + cli.name )
            runResults = runResults and run
        utilities.assert_equals( expect=main.TRUE, actual=runResults,
                                 onpass="Reran for election",
                                 onfail="Failed to rerun for election" )

        for node in main.activeNodes:
            main.log.warn( "\n****************** {} **************".format( main.nodes[ node ].ip_address ) )
            main.log.debug( main.CLIs[ node ].nodes( jsonFormat=False ) )
            main.log.debug( main.CLIs[ node ].leaders( jsonFormat=False ) )
            main.log.debug( main.CLIs[ node ].partitions( jsonFormat=False ) )
            main.log.debug( main.CLIs[ node ].apps( jsonFormat=False ) )

        main.step( "Reapplying cell variable to environment" )
        cellName = main.params[ 'ENV' ][ 'cellName' ]
        cellResult = main.ONOSbench.setCell( cellName )
        utilities.assert_equals( expect=main.TRUE, actual=cellResult,
                                 onpass="Set cell successfull",
                                 onfail="Failled to set cell" )

    def CASE7( self, main ):
        """
        Check state after ONOS scaling
        """

        main.HA.checkStateAfterONOS( main, afterWhich=1 )

        main.step( "Leadership Election is still functional" )
        # Test of LeadershipElection
        leaderList = []
        leaderResult = main.TRUE

        for i in main.activeNodes:
            cli = main.CLIs[ i ]
            leaderN = cli.electionTestLeader()
            leaderList.append( leaderN )
            if leaderN == main.FALSE:
                # error in response
                main.log.error( "Something is wrong with " +
                                 "electionTestLeader function, check the" +
                                 " error logs" )
                leaderResult = main.FALSE
            elif leaderN is None:
                main.log.error( cli.name +
                                 " shows no leader for the election-app." )
                leaderResult = main.FALSE
        if len( set( leaderList ) ) != 1:
            leaderResult = main.FALSE
            main.log.error(
                "Inconsistent view of leader for the election test app" )
            # TODO: print the list
        utilities.assert_equals(
            expect=main.TRUE,
            actual=leaderResult,
            onpass="Leadership election passed",
            onfail="Something went wrong with Leadership election" )

    def CASE8( self, main ):
        """
        Compare topo
        """
        main.HA.compareTopo( main )

    def CASE9( self, main ):
        """
        Link s3-s28 down
        """
        main.HA.linkDown( main )

    def CASE10( self, main ):
        """
        Link s3-s28 up
        """
        main.HA.linkUp( main )

    def CASE11( self, main ):
        """
        Switch Down
        """
        # NOTE: You should probably run a topology check after this
        main.HA.switchDown( main )

    def CASE12( self, main ):
        """
        Switch Up
        """
        # NOTE: You should probably run a topology check after this
        main.HA.switchUp( main )

    def CASE13( self, main ):
        """
        Clean up
        """
        main.HA.cleanUp( main )

        main.step( "Stopping webserver" )
        status = main.Server.stop()
        utilities.assert_equals( expect=main.TRUE, actual=status,
                                 onpass="Stop Server",
                                 onfail="Failled to stop SimpleHTTPServer" )
        del main.Server

    def CASE14( self, main ):
        """
        start election app on all onos nodes
        """
        main.HA.startElectionApp( main )

    def CASE15( self, main ):
        """
        Check that Leadership Election is still functional
            15.1 Run election on each node
            15.2 Check that each node has the same leaders and candidates
            15.3 Find current leader and withdraw
            15.4 Check that a new node was elected leader
            15.5 Check that that new leader was the candidate of old leader
            15.6 Run for election on old leader
            15.7 Check that oldLeader is a candidate, and leader if only 1 node
            15.8 Make sure that the old leader was added to the candidate list

            old and new variable prefixes refer to data from before vs after
                withdrawl and later before withdrawl vs after re-election
        """
        main.HA.isElectionFunctional( main )

    def CASE16( self, main ):
        """
        Install Distributed Primitives app
        """
        main.HA.installDistributedPrimitiveApp( main )

    def CASE17( self, main ):
        """
        Check for basic functionality with distributed primitives
        """
        main.HA.checkDistPrimitivesFunc( main )
